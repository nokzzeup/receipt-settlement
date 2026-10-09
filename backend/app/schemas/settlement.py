from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.expense import PersonOut
from app.settlement import BudgetState


class ReimbursableExpense(BaseModel):
    """승인됐고 아직 안 돌려준 지출"""

    id: int
    store_name: str | None
    paid_at: datetime | None
    amount: int


class PayerBalanceOut(BaseModel):
    payer: PersonOut
    to_reimburse: int  # 돌려줄 돈 (승인됐고 아직 안 돌려준 것)
    expenses: list[ReimbursableExpense]  # 그 지출들 (결제일 순). '보냈어요'는 이 목록 기준
    awaiting_approval: int  # 승인 대기 금액
    awaiting_count: int


class CategoryUsageOut(BaseModel):
    category_id: int
    name: str
    budget: int | None  # null = 예산 없음
    spent: int  # 집행액: 예산 기간 안 결제 + 승인된 지출
    awaiting: int  # 예산 기간 안 승인 대기
    remaining: int | None  # 예산 - 집행액 (넘었으면 음수)
    state: BudgetState


class BudgetPeriodOut(BaseModel):
    start: date
    end: date


class SettlementOut(BaseModel):
    """정산 화면 + 홈 '돌려받을 돈'.

    scope: 총무·승인자는 조직 전체("org"), 구성원은 내 것만("me") — payers·합계가 그 범위.
    계정별 예산 사용(categories)은 모두에게 조직 전체로 보인다.
    """

    scope: Literal["org", "me"]
    to_reimburse: int  # 범위 안 돌려줄 돈 합계
    to_reimburse_count: int  # 그 지출 수
    awaiting_approval: int  # 범위 안 승인 대기 금액
    awaiting_count: int
    payers: list[PayerBalanceOut]  # 돌려줄 돈·승인 대기가 있는 결제자
    me: PayerBalanceOut  # 내 몫 (없으면 0원)
    period: BudgetPeriodOut | None  # 예산 기간 (null = 전체 누적)
    categories: list[CategoryUsageOut]
    budget_total: int | None  # 예산을 정한 계정과목의 예산 합 (하나도 없으면 null)
    spent_total: int  # 모든 계정과목 집행액 합
    awaiting_total: int  # 모든 계정과목 승인 대기 합 (기간 안)


class BulkReimburseRequest(BaseModel):
    """결제자 한 명에게 한 번에 보낸 것으로 표시. 화면에서 본 지출 목록을 그대로 보낸다
    (그 사이 새로 승인된 지출이 섞여 들어가지 않게)"""

    payer_membership_id: int
    expense_ids: list[int] = Field(min_length=1, max_length=500)


class BulkReimburseResult(BaseModel):
    count: int
    amount: int
