"""지출: 영수증 업로드(→ 작성 중 지출), 목록, 상세, 저장, 삭제, 제출, 원본 이미지.

흐름: 영수증 업로드 → OCR·파싱 결과로 작성 중(DRAFT) 지출이 바로 생김 → 확인·수정 화면에서 저장(PUT)
      → 제출(SUBMITTED) → (5단계) 승인/반려 → 환급

권한
- 업로드: 그 조직 구성원 누구나. 결제자(환급받을 사람) 기본값은 올린 사람
- 보기: 총무·승인자는 전부, 구성원은 내가 올렸거나 내가 결제자인 지출만 (아니면 404)
- 저장·삭제·제출: 작성 중일 때만, 올린 사람 또는 총무
- 결제자·계정과목은 같은 조직 것만 허용 (DB가 못 막으므로 여기서 검증)
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import aliased

from app.api.deps import CurrentMembership, DbSession, OcrEngineDep
from app.models import (
    ApprovalAction,
    ApprovalLog,
    Category,
    CategorySource,
    Expense,
    ExpenseItem,
    ExpenseStatus,
    Membership,
    MembershipRole,
    Receipt,
    User,
)
from app.ocr import OcrRawResult
from app.parsing.rows import row_texts
from app.receipts import storage
from app.receipts.images import MAX_UPLOAD_BYTES, MEDIA_TYPES, detect_image_type, is_heif
from app.receipts.intake import create_draft_expense
from app.schemas.expense import (
    ExpenseDetail,
    ExpenseItemOut,
    ExpenseSummary,
    ExpenseUpdate,
    PersonOut,
    ReceiptOut,
)

router = APIRouter(prefix="/orgs/{org_id}", tags=["expenses"])

_SEE_ALL_ROLES = {MembershipRole.TREASURER, MembershipRole.APPROVER}


# ---------- 권한 ----------


def _visible_condition(me: Membership) -> ColumnElement[bool] | None:
    """목록 조회용 조건. None = 조직 지출 전부"""
    if me.role in _SEE_ALL_ROLES:
        return None
    return or_(Expense.payer_membership_id == me.id, Receipt.uploader_membership_id == me.id)


def _can_view(me: Membership, expense: Expense) -> bool:
    return (
        me.role in _SEE_ALL_ROLES
        or expense.payer_membership_id == me.id
        or expense.receipt.uploader_membership_id == me.id
    )


def _is_owner_or_treasurer(me: Membership, expense: Expense) -> bool:
    return me.role == MembershipRole.TREASURER or expense.receipt.uploader_membership_id == me.id


def _can_edit(me: Membership, expense: Expense) -> bool:
    return expense.status == ExpenseStatus.DRAFT and _is_owner_or_treasurer(me, expense)


def _get_visible(db: DbSession, org_id: int, expense_id: int, me: Membership) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None or expense.organization_id != org_id or not _can_view(me, expense):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "지출을 찾을 수 없습니다.")
    return expense


def _get_editable(db: DbSession, org_id: int, expense_id: int, me: Membership, action: str) -> Expense:
    expense = _get_visible(db, org_id, expense_id, me)
    if not _is_owner_or_treasurer(me, expense):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"영수증을 올린 사람이나 총무만 {action}할 수 있습니다.")
    if expense.status != ExpenseStatus.DRAFT:
        raise HTTPException(status.HTTP_409_CONFLICT, f"작성 중인 지출만 {action}할 수 있습니다.")
    return expense


# ---------- 응답 만들기 ----------


def _person(membership: Membership) -> PersonOut:
    return PersonOut(membership_id=membership.id, name=membership.user.name)


def _receipt_out(receipt: Receipt) -> ReceiptOut:
    raw = OcrRawResult.model_validate(receipt.ocr_raw) if receipt.ocr_raw else None
    return ReceiptOut(
        id=receipt.id,
        store_name=receipt.store_name,
        paid_at=receipt.paid_at,
        total_amount=receipt.total_amount,
        ocr_failed=raw is None,
        ocr_text=row_texts(raw) if raw else [],
        uploaded_at=receipt.created_at,
    )


def _detail(expense: Expense, me: Membership) -> ExpenseDetail:
    return ExpenseDetail(
        id=expense.id,
        status=expense.status,
        reject_reason=expense.reject_reason,
        reimbursed_at=expense.reimbursed_at,
        amount=sum(item.amount for item in expense.items),
        payer=_person(expense.payer),
        uploader=_person(expense.receipt.uploader),
        receipt=_receipt_out(expense.receipt),
        items=[ExpenseItemOut.model_validate(item) for item in expense.items],
        can_edit=_can_edit(me, expense),
        created_at=expense.created_at,
        updated_at=expense.updated_at,
    )


def _won(value: int) -> str:
    return f"{value:,}원"


# ---------- API ----------


@router.post(
    "/receipts",
    status_code=status.HTTP_201_CREATED,
    responses={413: {"description": "15MB 초과"}, 415: {"description": "JPG·PNG·WEBP가 아님"}},
)
def upload_receipt(
    org_id: int,
    image: Annotated[UploadFile, File(description="영수증 사진 (JPG·PNG·WEBP, 15MB 이하)")],
    me: CurrentMembership,
    db: DbSession,
    engine: OcrEngineDep,
) -> ExpenseDetail:
    """영수증 사진 업로드 → OCR → 작성 중(DRAFT) 지출 생성. 인식에 실패해도 빈 값으로 만들어진다"""
    data = image.file.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "빈 파일입니다.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "사진 용량이 너무 큽니다. (최대 15MB)")
    image_type = detect_image_type(data)
    if image_type is None:
        if is_heif(data):
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                "HEIC(아이폰 기본 형식) 사진은 아직 받을 수 없어요. 앱에서 바로 촬영하거나 JPG로 바꿔서 올려주세요.",
            )
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "JPG, PNG, WEBP 사진만 올릴 수 있습니다.")
    expense = create_draft_expense(db, me, data, image_type, engine)
    return _detail(expense, me)


@router.get("/expenses")
def list_expenses(org_id: int, me: CurrentMembership, db: DbSession) -> list[ExpenseSummary]:
    """내가 볼 수 있는 지출 (최근 등록 순)"""
    item_sum = (
        select(func.coalesce(func.sum(ExpenseItem.amount), 0))
        .where(ExpenseItem.expense_id == Expense.id)
        .correlate(Expense)
        .scalar_subquery()
    )
    item_count = (
        select(func.count(ExpenseItem.id))
        .where(ExpenseItem.expense_id == Expense.id)
        .correlate(Expense)
        .scalar_subquery()
    )
    uncategorized = (
        select(func.count(ExpenseItem.id))
        .where(ExpenseItem.expense_id == Expense.id, ExpenseItem.category_id.is_(None))
        .correlate(Expense)
        .scalar_subquery()
    )
    payer = aliased(Membership)
    payer_user = aliased(User)
    query = (
        select(Expense, Receipt, payer.id, payer_user.name, item_sum, item_count, uncategorized)
        .join(Receipt, Receipt.id == Expense.receipt_id)
        .join(payer, payer.id == Expense.payer_membership_id)
        .join(payer_user, payer_user.id == payer.user_id)
        .where(Expense.organization_id == org_id)
        .order_by(Expense.created_at.desc(), Expense.id.desc())
    )
    if (condition := _visible_condition(me)) is not None:
        query = query.where(condition)
    return [
        ExpenseSummary(
            id=expense.id,
            status=expense.status,
            store_name=receipt.store_name,
            paid_at=receipt.paid_at,
            amount=amount,
            item_count=count,
            uncategorized_count=uncategorized_count,
            payer=PersonOut(membership_id=payer_id, name=payer_name),
            reimbursed_at=expense.reimbursed_at,
            created_at=expense.created_at,
        )
        for expense, receipt, payer_id, payer_name, amount, count, uncategorized_count in db.execute(query)
    ]


@router.get("/expenses/{expense_id}")
def get_expense(org_id: int, expense_id: int, me: CurrentMembership, db: DbSession) -> ExpenseDetail:
    return _detail(_get_visible(db, org_id, expense_id, me), me)


@router.put("/expenses/{expense_id}")
def update_expense(
    org_id: int, expense_id: int, body: ExpenseUpdate, me: CurrentMembership, db: DbSession
) -> ExpenseDetail:
    """확인·수정한 내용 저장 (작성 중일 때만). 품목은 보낸 목록으로 통째로 교체"""
    expense = _get_editable(db, org_id, expense_id, me, "수정")

    payer = db.get(Membership, body.payer_membership_id)
    if payer is None or payer.organization_id != org_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "결제자는 이 조직의 구성원이어야 합니다.")

    category_ids = {item.category_id for item in body.items if item.category_id is not None}
    if category_ids:
        found = set(
            db.scalars(select(Category.id).where(Category.organization_id == org_id, Category.id.in_(category_ids)))
        )
        if found != category_ids:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "없는 계정과목이 있습니다. 화면을 새로고침한 뒤 다시 고르세요."
            )

    # 자동 분류(4단계) 결과를 그대로 둔 품목은 AUTO 유지, 사용자가 고르거나 바꾼 건 MANUAL
    kept_auto = {(i.name, i.category_id) for i in expense.items if i.category_source == CategorySource.AUTO}

    def source(name: str, category_id: int | None) -> CategorySource | None:
        if category_id is None:
            return None
        return CategorySource.AUTO if (name, category_id) in kept_auto else CategorySource.MANUAL

    expense.items = [
        ExpenseItem(
            name=item.name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            amount=item.amount,
            category_id=item.category_id,
            category_source=source(item.name, item.category_id),
        )
        for item in body.items
    ]
    receipt = expense.receipt
    receipt.store_name = body.store_name
    receipt.paid_at = body.paid_at
    receipt.total_amount = body.total_amount
    expense.payer_membership_id = payer.id
    expense.updated_at = datetime.now(UTC)  # 품목만 바뀌어도 수정 시각이 갱신되게
    db.commit()
    return _detail(expense, me)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(org_id: int, expense_id: int, me: CurrentMembership, db: DbSession) -> Response:
    """작성 중 지출 삭제 (영수증 기록·원본 이미지도 같이)"""
    expense = _get_editable(db, org_id, expense_id, me, "삭제")
    receipt = expense.receipt
    image_path = receipt.image_path
    db.delete(expense)
    db.delete(receipt)
    db.commit()
    storage.delete_image(image_path)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/expenses/{expense_id}/submit")
def submit_expense(org_id: int, expense_id: int, me: CurrentMembership, db: DbSession) -> ExpenseDetail:
    """제출 → 승인 대기. 저장된 내용 기준으로 빠진 값이 있으면 422 (무엇이 빠졌는지 메시지로)"""
    expense = _get_editable(db, org_id, expense_id, me, "제출")
    receipt = expense.receipt
    problems: list[str] = []

    missing = [
        label
        for label, value in (
            ("가게명", receipt.store_name),
            ("결제일시", receipt.paid_at),
            ("영수증 합계", receipt.total_amount),
        )
        if value is None
    ]
    if missing:
        problems.append(f"{'·'.join(missing)}을(를) 입력하세요.")
    if not expense.items:
        problems.append("품목을 1개 이상 입력하세요.")
    uncategorized = sum(1 for item in expense.items if item.category_id is None)
    if uncategorized:
        problems.append(f"계정과목을 정하지 않은 품목이 {uncategorized}개 있습니다.")
    amount = sum(item.amount for item in expense.items)
    if expense.items and amount <= 0:
        problems.append("청구 금액이 0원 이하입니다.")
    if receipt.total_amount is not None and amount > receipt.total_amount:
        problems.append(f"청구 금액({_won(amount)})이 영수증 합계({_won(receipt.total_amount)})보다 큽니다.")
    if problems:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, " ".join(problems))

    expense.status = ExpenseStatus.SUBMITTED
    expense.approval_logs.append(ApprovalLog(actor_membership_id=me.id, action=ApprovalAction.SUBMIT))
    db.commit()
    return _detail(expense, me)


@router.get(
    "/expenses/{expense_id}/image",
    response_class=FileResponse,
    responses={200: {"content": {t: {} for t in MEDIA_TYPES.values()}, "description": "영수증 원본 이미지"}},
)
def get_receipt_image(org_id: int, expense_id: int, me: CurrentMembership, db: DbSession) -> FileResponse:
    """영수증 원본 이미지 (지출을 볼 수 있는 사람만)"""
    expense = _get_visible(db, org_id, expense_id, me)
    path = storage.resolve(expense.receipt.image_path)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "원본 이미지 파일이 없습니다.")
    media_type = MEDIA_TYPES.get(path.suffix.lstrip("."), "application/octet-stream")
    # 같은 지출의 이미지는 바뀌지 않으므로 브라우저 캐시 허용 (로그인한 본인 브라우저에만)
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "private, max-age=86400"})
