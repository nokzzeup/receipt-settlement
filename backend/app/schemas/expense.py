from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.models.enums import ApprovalAction, CategorySource, ExpenseStatus
from app.schemas.common import (
    MAX_ITEMS,
    NonNegativeWon,
    OptionalText200,
    OptionalText500,
    Quantity,
    Text200,
    Text500,
    Won,
)


class PersonOut(BaseModel):
    membership_id: int
    name: str


class ExpenseItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    quantity: int
    unit_price: int | None
    amount: int
    category_id: int | None  # null = 미분류
    category_source: CategorySource | None


class ReceiptOut(BaseModel):
    id: int
    # 영수증에 찍힌 값 (확인·수정 후)
    store_name: str | None
    paid_at: datetime | None
    total_amount: int | None
    ocr_failed: bool  # true면 자동 인식 실패 → 직접 입력
    ocr_text: list[str]  # 인식된 원문 (행 단위, 카드번호 마스킹됨). 수정할 때 참고용
    uploaded_at: datetime


class HistoryEntryOut(BaseModel):
    """제출·승인·반려·환급 기록 한 줄 (오래된 순)"""

    action: ApprovalAction
    actor: PersonOut
    comment: str | None  # 반려 사유, 승인 메모
    created_at: datetime


class BudgetWarningOut(BaseModel):
    """이 지출을 승인하면 예산을 넘는 계정과목"""

    category_id: int
    category_name: str
    budget: int
    spent: int  # 이 지출을 빼고 이미 승인된 집행액 (예산 기간 안)
    this_amount: int  # 이 지출에서 그 계정과목 금액
    over_by: int  # 승인하면 넘는 금액


class ExpenseDetail(BaseModel):
    id: int
    status: ExpenseStatus
    reject_reason: str | None  # 반려됐을 때 (다시 제출하면 지워지고 기록에만 남음)
    reimbursed_at: datetime | None
    reimbursed_by: PersonOut | None
    amount: int  # 청구(환급) 금액 = 품목 금액 합계
    payer: PersonOut  # 결제자 = 환급받을 사람
    uploader: PersonOut
    receipt: ReceiptOut
    items: list[ExpenseItemOut]
    history: list[HistoryEntryOut]
    # 내가 지금 할 수 있는 일 (서버가 같은 기준으로 다시 확인함)
    can_edit: bool  # 작성 중·반려됨 + 올린 사람 또는 총무 → 수정·삭제·제출
    can_withdraw: bool  # 승인 대기 + 올린 사람 또는 총무 → 제출 취소
    can_review: bool  # 승인 대기 + 총무·승인자 → 승인·반려
    can_unapprove: bool  # 승인됨·환급 전 + 총무·승인자 → 승인 취소
    can_reimburse: bool  # 승인됨·환급 전 + 총무 → 환급 완료
    can_unreimburse: bool  # 환급 완료 + 총무 → 환급 완료 취소
    # 승인 대기이고 내가 승인할 수 있을 때만 채움
    budget_warnings: list[BudgetWarningOut]
    created_at: datetime
    updated_at: datetime


class ExpenseSummary(BaseModel):
    """지출 목록의 한 줄"""

    id: int
    status: ExpenseStatus
    store_name: str | None
    paid_at: datetime | None
    amount: int
    item_count: int
    uncategorized_count: int  # 계정과목을 안 정한 품목 수
    # 품목 금액 합이 가장 큰 계정과목 (목록 아이콘용). 계정과목을 정한 품목이 없으면 None
    main_category_id: int | None
    payer: PersonOut
    reimbursed_at: datetime | None
    created_at: datetime


class ExpenseItemIn(BaseModel):
    name: Text200
    quantity: Quantity = 1
    unit_price: Won | None = None
    amount: Won  # 할인 줄은 음수 가능
    category_id: int | None = None


class ExpenseUpdate(BaseModel):
    """작성 중 지출 저장 (전체 교체). 품목 목록도 보낸 것으로 통째로 바뀐다"""

    store_name: OptionalText200 = None
    paid_at: AwareDatetime | None = Field(default=None, description="시간대 포함 (예: 2026-09-28T14:32:00+09:00)")
    total_amount: NonNegativeWon | None = None
    payer_membership_id: int
    items: list[ExpenseItemIn] = Field(max_length=MAX_ITEMS)


class ReviewRequest(BaseModel):
    """승인·승인 취소 (메모는 선택)"""

    comment: OptionalText500 = None


class RejectRequest(BaseModel):
    reason: Text500 = Field(description="반려 사유 (올린 사람에게 보임)")
