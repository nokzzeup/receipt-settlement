"""지출: 영수증 업로드(→ 작성 중 지출), 목록, 상세, 저장, 삭제, 원본 이미지 + 제출·승인·반려·환급.

흐름: 영수증 업로드 → OCR·파싱·자동 분류 결과로 작성 중(DRAFT) 지출이 바로 생김 → 확인·수정(PUT)
      → 제출(SUBMITTED) → 승인(APPROVED) → 환급 완료(reimbursed_at)
                         ↘ 반려(REJECTED) → 고쳐서 다시 제출
      되돌리기: 제출 취소(SUBMITTED → DRAFT), 승인 취소(APPROVED → SUBMITTED, 환급 전만), 환급 완료 취소

권한
- 업로드: 그 조직 구성원 누구나. 결제자(환급받을 사람) 기본값은 올린 사람
- 보기: 총무는 전부, 승인자는 남의 작성 중 지출만 빼고 전부, 구성원은 내가 올렸거나 내가 결제자인 지출만 (아니면 404)
- 저장·삭제·제출: 작성 중·반려됨일 때, 올린 사람 또는 총무. 제출 취소도 같은 사람
- 승인·반려·승인 취소: 총무·승인자 (자기 지출도 가능 — 작은 조직에서 막으면 승인할 사람이 없음. 기록은 남음)
- 환급 완료·취소: 총무
- 결제자·계정과목은 같은 조직 것만 허용 (DB가 못 막으므로 여기서 검증)
- 상태를 바꾸는 일은 전부 결재 이력(ApprovalLog)에 남긴다
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import aliased

from app.api.deps import CurrentMembership, DbSession, OcrEngineDep, ReviewerMembership, TreasurerMembership
from app.classify import learn_from_items
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
    Organization,
    Receipt,
    User,
)
from app.ocr import OcrRawResult
from app.parsing.rows import row_texts
from app.receipts import storage
from app.receipts.images import MAX_UPLOAD_BYTES, MEDIA_TYPES, detect_image_type, is_heif
from app.receipts.duplicates import DuplicateMatch, find_duplicates
from app.receipts.intake import create_draft_expense
from app.schemas.expense import (
    BudgetWarningOut,
    DuplicateOut,
    ExpenseDetail,
    ExpenseItemOut,
    ExpenseSummary,
    ExpenseUpdate,
    HistoryEntryOut,
    PersonOut,
    ReceiptOut,
    RejectRequest,
    ReviewRequest,
)
from app.settlement import approval_warnings, budget_period, category_budgets, load_categories, load_expense_records

router = APIRouter(prefix="/orgs/{org_id}", tags=["expenses"])

_REVIEWER_ROLES = {MembershipRole.TREASURER, MembershipRole.APPROVER}
# 고칠 수 있는 상태: 작성 중, 반려됨(고쳐서 다시 제출)
_EDITABLE = {ExpenseStatus.DRAFT, ExpenseStatus.REJECTED}


# ---------- 권한 ----------


def _mine_condition(me: Membership) -> ColumnElement[bool]:
    return or_(Expense.payer_membership_id == me.id, Receipt.uploader_membership_id == me.id)


def _visible_condition(me: Membership) -> ColumnElement[bool] | None:
    """목록 조회용 조건. None = 조직 지출 전부"""
    if me.role == MembershipRole.TREASURER:
        return None
    if me.role == MembershipRole.APPROVER:
        return or_(Expense.status != ExpenseStatus.DRAFT, _mine_condition(me))
    return _mine_condition(me)


def _is_mine(me: Membership, expense: Expense) -> bool:
    return expense.payer_membership_id == me.id or expense.receipt.uploader_membership_id == me.id


def _can_view(me: Membership, expense: Expense) -> bool:
    if me.role == MembershipRole.TREASURER or _is_mine(me, expense):
        return True
    return me.role == MembershipRole.APPROVER and expense.status != ExpenseStatus.DRAFT


def _is_owner_or_treasurer(me: Membership, expense: Expense) -> bool:
    return me.role == MembershipRole.TREASURER or expense.receipt.uploader_membership_id == me.id


def _can_edit(me: Membership, expense: Expense) -> bool:
    return expense.status in _EDITABLE and _is_owner_or_treasurer(me, expense)


def _awaiting_reimbursement(expense: Expense) -> bool:
    return expense.status == ExpenseStatus.APPROVED and expense.reimbursed_at is None


def _get_visible(db: DbSession, org_id: int, expense_id: int, me: Membership) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None or expense.organization_id != org_id or not _can_view(me, expense):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "지출을 찾을 수 없습니다.")
    return expense


def _get_editable(db: DbSession, org_id: int, expense_id: int, me: Membership, action: str) -> Expense:
    expense = _get_visible(db, org_id, expense_id, me)
    if not _is_owner_or_treasurer(me, expense):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"영수증을 올린 사람이나 총무만 {action}할 수 있습니다.")
    if expense.status not in _EDITABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, f"작성 중이거나 반려된 지출만 {action}할 수 있습니다.")
    return expense


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail)


def _log(expense: Expense, me: Membership, action: ApprovalAction, comment: str | None = None) -> None:
    expense.approval_logs.append(ApprovalLog(actor_membership_id=me.id, action=action, comment=comment))


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


def _budget_warnings(db: DbSession, expense: Expense) -> list[BudgetWarningOut]:
    """승인하면 예산을 넘는 계정과목 (정산 엔진 규칙 그대로)"""
    org = db.get_one(Organization, expense.organization_id)
    categories = load_categories(db, org.id)
    records = load_expense_records(db, org.id)
    target = next((r for r in records if r.id == expense.id), None)
    if target is None:
        return []
    names = {c.id: c.name for c in categories}
    return [
        BudgetWarningOut(
            category_id=w.category_id,
            category_name=names[w.category_id],
            budget=w.budget,
            spent=w.spent,
            this_amount=w.this_amount,
            over_by=w.over_by,
        )
        for w in approval_warnings(target, category_budgets(categories), records, budget_period(org))
    ]


def _duplicate_out(match: DuplicateMatch, me: Membership) -> DuplicateOut | None:
    other = match.receipt.expense
    if other is None:
        return None
    return DuplicateOut(
        expense_id=other.id if _can_view(me, other) else None,
        reason=match.reason,
        store_name=match.receipt.store_name,
        paid_at=match.receipt.paid_at,
        total_amount=match.receipt.total_amount,
        status=other.status,
        uploader_name=match.receipt.uploader.user.name,
    )


def _detail(db: DbSession, expense: Expense, me: Membership) -> ExpenseDetail:
    is_reviewer = me.role in _REVIEWER_ROLES
    is_treasurer = me.role == MembershipRole.TREASURER
    submitted = expense.status == ExpenseStatus.SUBMITTED
    can_review = submitted and is_reviewer
    return ExpenseDetail(
        id=expense.id,
        status=expense.status,
        reject_reason=expense.reject_reason,
        reimbursed_at=expense.reimbursed_at,
        reimbursed_by=_person(expense.reimbursed_by) if expense.reimbursed_by else None,
        amount=sum(item.amount for item in expense.items),
        payer=_person(expense.payer),
        uploader=_person(expense.receipt.uploader),
        receipt=_receipt_out(expense.receipt),
        items=[ExpenseItemOut.model_validate(item) for item in expense.items],
        history=[
            HistoryEntryOut(action=log.action, actor=_person(log.actor), comment=log.comment, created_at=log.created_at)
            for log in expense.approval_logs
        ],
        can_edit=_can_edit(me, expense),
        can_withdraw=submitted and _is_owner_or_treasurer(me, expense),
        can_review=can_review,
        can_unapprove=_awaiting_reimbursement(expense) and is_reviewer,
        can_reimburse=_awaiting_reimbursement(expense) and is_treasurer,
        can_unreimburse=expense.reimbursed_at is not None and is_treasurer,
        budget_warnings=_budget_warnings(db, expense) if can_review else [],
        duplicates=[d for m in find_duplicates(db, expense.receipt) if (d := _duplicate_out(m, me)) is not None],
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
    return _detail(db, expense, me)


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
    # 금액 합이 가장 큰 계정과목 (같으면 id가 작은 쪽). 할인(음수) 줄도 합에 포함
    main_category = (
        select(ExpenseItem.category_id)
        .where(ExpenseItem.expense_id == Expense.id, ExpenseItem.category_id.is_not(None))
        .group_by(ExpenseItem.category_id)
        .order_by(func.sum(ExpenseItem.amount).desc(), ExpenseItem.category_id)
        .limit(1)
        .correlate(Expense)
        .scalar_subquery()
    )
    payer = aliased(Membership)
    payer_user = aliased(User)
    query = (
        select(Expense, Receipt, payer.id, payer_user.name, item_sum, item_count, uncategorized, main_category)
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
            main_category_id=main_category_id,
            payer=PersonOut(membership_id=payer_id, name=payer_name),
            reimbursed_at=expense.reimbursed_at,
            created_at=expense.created_at,
        )
        for expense, receipt, payer_id, payer_name, amount, count, uncategorized_count, main_category_id in db.execute(
            query
        )
    ]


@router.get("/expenses/{expense_id}")
def get_expense(org_id: int, expense_id: int, me: CurrentMembership, db: DbSession) -> ExpenseDetail:
    return _detail(db, _get_visible(db, org_id, expense_id, me), me)


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
    return _detail(db, expense, me)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(org_id: int, expense_id: int, me: CurrentMembership, db: DbSession) -> Response:
    """작성 중·반려된 지출 삭제 (영수증 기록·원본 이미지·결재 이력도 같이)"""
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
    """제출(작성 중·반려됨 → 승인 대기). 저장된 내용 기준으로 빠진 값이 있으면 422 (무엇이 빠졌는지 메시지로)"""
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
    expense.reject_reason = None  # 반려 뒤 다시 제출: 사유는 결재 이력에 남아 있음
    _log(expense, me, ApprovalAction.SUBMIT)
    # 사용자가 직접 고른 계정과목을 조직 규칙으로 저장 → 다음 영수증부터 자동 분류에 반영
    learn_from_items(db, org_id, expense.items)
    db.commit()
    return _detail(db, expense, me)


@router.post("/expenses/{expense_id}/withdraw")
def withdraw_expense(org_id: int, expense_id: int, me: CurrentMembership, db: DbSession) -> ExpenseDetail:
    """제출 취소 (승인 대기 → 작성 중). 승인·반려되기 전에만, 올린 사람 또는 총무"""
    expense = _get_visible(db, org_id, expense_id, me)
    if not _is_owner_or_treasurer(me, expense):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "영수증을 올린 사람이나 총무만 제출을 취소할 수 있습니다.")
    if expense.status != ExpenseStatus.SUBMITTED:
        raise _conflict("승인 대기 중인 지출만 제출을 취소할 수 있습니다.")
    expense.status = ExpenseStatus.DRAFT
    _log(expense, me, ApprovalAction.WITHDRAW)
    db.commit()
    return _detail(db, expense, me)


@router.post("/expenses/{expense_id}/approve")
def approve_expense(
    org_id: int, expense_id: int, body: ReviewRequest, me: ReviewerMembership, db: DbSession
) -> ExpenseDetail:
    """승인 (승인 대기 → 승인됨 = 환급 대상). 예산을 넘어도 승인은 된다 (경고는 상세의 budget_warnings)"""
    expense = _get_visible(db, org_id, expense_id, me)
    if expense.status != ExpenseStatus.SUBMITTED:
        raise _conflict("승인 대기 중인 지출만 승인할 수 있습니다.")
    expense.status = ExpenseStatus.APPROVED
    _log(expense, me, ApprovalAction.APPROVE, body.comment)
    db.commit()
    return _detail(db, expense, me)


@router.post("/expenses/{expense_id}/reject")
def reject_expense(
    org_id: int, expense_id: int, body: RejectRequest, me: ReviewerMembership, db: DbSession
) -> ExpenseDetail:
    """반려 (승인 대기 → 반려됨). 사유 필수 → 올린 사람이 고쳐서 다시 제출하거나 삭제"""
    expense = _get_visible(db, org_id, expense_id, me)
    if expense.status != ExpenseStatus.SUBMITTED:
        raise _conflict("승인 대기 중인 지출만 반려할 수 있습니다.")
    expense.status = ExpenseStatus.REJECTED
    expense.reject_reason = body.reason
    _log(expense, me, ApprovalAction.REJECT, body.reason)
    db.commit()
    return _detail(db, expense, me)


@router.post("/expenses/{expense_id}/unapprove")
def unapprove_expense(
    org_id: int, expense_id: int, body: ReviewRequest, me: ReviewerMembership, db: DbSession
) -> ExpenseDetail:
    """승인 취소 (승인됨 → 승인 대기). 돌려주기 전에만"""
    expense = _get_visible(db, org_id, expense_id, me)
    if expense.status != ExpenseStatus.APPROVED:
        raise _conflict("승인된 지출만 승인을 취소할 수 있습니다.")
    if expense.reimbursed_at is not None:
        raise _conflict("이미 돌려준 지출이에요. 환급 완료를 먼저 취소하세요.")
    expense.status = ExpenseStatus.SUBMITTED
    _log(expense, me, ApprovalAction.UNAPPROVE, body.comment)
    db.commit()
    return _detail(db, expense, me)


@router.post("/expenses/{expense_id}/reimbursement")
def reimburse_expense(org_id: int, expense_id: int, me: TreasurerMembership, db: DbSession) -> ExpenseDetail:
    """환급 완료로 표시 (총무). 실제 송금은 앱 밖에서 하고, 여기선 보낸 것만 기록"""
    expense = _get_visible(db, org_id, expense_id, me)
    if expense.status != ExpenseStatus.APPROVED:
        raise _conflict("승인된 지출만 환급 완료로 표시할 수 있습니다.")
    if expense.reimbursed_at is not None:
        raise _conflict("이미 환급 완료로 표시된 지출입니다.")
    expense.reimbursed_at = datetime.now(UTC)
    expense.reimbursed_by_membership_id = me.id
    _log(expense, me, ApprovalAction.REIMBURSE)
    db.commit()
    return _detail(db, expense, me)


@router.delete("/expenses/{expense_id}/reimbursement")
def unreimburse_expense(org_id: int, expense_id: int, me: TreasurerMembership, db: DbSession) -> ExpenseDetail:
    """환급 완료 취소 (총무, 잘못 누른 경우)"""
    expense = _get_visible(db, org_id, expense_id, me)
    if expense.reimbursed_at is None:
        raise _conflict("환급 완료로 표시되지 않은 지출입니다.")
    expense.reimbursed_at = None
    expense.reimbursed_by_membership_id = None
    _log(expense, me, ApprovalAction.UNREIMBURSE)
    db.commit()
    return _detail(db, expense, me)


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
