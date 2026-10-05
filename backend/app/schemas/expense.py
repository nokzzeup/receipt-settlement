from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.models.enums import CategorySource, ExpenseStatus
from app.schemas.common import MAX_ITEMS, NonNegativeWon, OptionalText200, Quantity, Text200, Won


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


class ExpenseDetail(BaseModel):
    id: int
    status: ExpenseStatus
    reject_reason: str | None
    reimbursed_at: datetime | None
    amount: int  # 청구(환급) 금액 = 품목 금액 합계
    payer: PersonOut  # 결제자 = 환급받을 사람
    uploader: PersonOut
    receipt: ReceiptOut
    items: list[ExpenseItemOut]
    can_edit: bool  # 작성 중이고, 내가 올린 사람이거나 총무
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
