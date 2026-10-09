"""정산 엔진 — 순수 계산 (DB를 모름 → 단위 테스트로 규칙을 고정한다. tests/test_settlement_engine.py)

규칙
- 금액은 int만. 지출 금액 = 품목 금액 합 (할인 줄은 음수)
- 돌려줄 돈(환급 대상) = 승인됐고(APPROVED) 아직 안 돌려준(reimbursed=False) 지출. **예산 기간과 상관없이 전부**
  (지난 기간 지출이라도 안 돌려줬으면 갚아야 하므로)
- 계정별 집행액 = 예산 기간 안에 결제한(한국 날짜 기준, 양 끝 포함) 승인된 지출의 품목 금액 합 (돌려줬는지와 무관)
- 승인 대기(SUBMITTED)는 집행액에 넣지 않고 따로 보여준다 → "승인하면 넘을 것 같음" 경고에 씀
- 작성 중(DRAFT)·반려(REJECTED)는 어디에도 안 셈
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.core.timezone import KST
from app.models.enums import ExpenseStatus


@dataclass(frozen=True)
class ItemLine:
    category_id: int | None
    amount: int


@dataclass(frozen=True)
class ExpenseRecord:
    id: int
    payer_id: int  # 결제자 membership id
    status: ExpenseStatus
    reimbursed: bool
    paid_at: datetime | None  # 영수증 결제일시 (timezone-aware)
    items: tuple[ItemLine, ...]

    @property
    def amount(self) -> int:
        return sum(item.amount for item in self.items)

    @property
    def awaiting_reimbursement(self) -> bool:
        return self.status == ExpenseStatus.APPROVED and not self.reimbursed


@dataclass(frozen=True)
class BudgetPeriod:
    start: date
    end: date

    def contains(self, paid_at: datetime | None) -> bool:
        if paid_at is None:
            return False
        return self.start <= paid_at.astimezone(KST).date() <= self.end


def in_period(expense: ExpenseRecord, period: BudgetPeriod | None) -> bool:
    return period is None or period.contains(expense.paid_at)


# ---------- 결제자별 돌려줄 돈 ----------


@dataclass(frozen=True)
class PayerBalance:
    payer_id: int
    to_reimburse: int  # 승인됐고 아직 안 돌려준 금액
    reimbursable_ids: tuple[int, ...]  # 그 지출들 (결제일 순)
    awaiting_approval: int  # 승인 대기 금액
    awaiting_count: int


def payer_balances(expenses: Iterable[ExpenseRecord]) -> list[PayerBalance]:
    """돌려줄 돈이나 승인 대기가 있는 결제자만. 돌려줄 돈 많은 순 → 승인 대기 많은 순 → id 순"""
    reimbursable: dict[int, list[ExpenseRecord]] = defaultdict(list)
    awaiting: dict[int, list[ExpenseRecord]] = defaultdict(list)
    for expense in expenses:
        if expense.awaiting_reimbursement:
            reimbursable[expense.payer_id].append(expense)
        elif expense.status == ExpenseStatus.SUBMITTED:
            awaiting[expense.payer_id].append(expense)

    balances = []
    for payer_id in reimbursable.keys() | awaiting.keys():
        mine = sorted(reimbursable[payer_id], key=_paid_order)
        waiting = awaiting[payer_id]
        balances.append(
            PayerBalance(
                payer_id=payer_id,
                to_reimburse=sum(e.amount for e in mine),
                reimbursable_ids=tuple(e.id for e in mine),
                awaiting_approval=sum(e.amount for e in waiting),
                awaiting_count=len(waiting),
            )
        )
    return sorted(balances, key=lambda b: (-b.to_reimburse, -b.awaiting_approval, b.payer_id))


def _paid_order(expense: ExpenseRecord) -> tuple[bool, datetime | None, int]:
    return (expense.paid_at is None, expense.paid_at, expense.id)


# ---------- 계정별 예산 ----------


class BudgetState(StrEnum):
    NO_BUDGET = "NO_BUDGET"  # 예산을 안 정함
    OK = "OK"
    AT_RISK = "AT_RISK"  # 지금은 안 넘었지만 승인 대기까지 승인하면 넘음
    OVER = "OVER"  # 승인된 것만으로 넘음


@dataclass(frozen=True)
class CategoryBudget:
    id: int
    budget: int | None  # None = 예산 없음


@dataclass(frozen=True)
class CategoryUsage:
    category_id: int
    budget: int | None
    spent: int  # 집행액: 기간 안 승인된 지출
    awaiting: int  # 기간 안 승인 대기

    @property
    def remaining(self) -> int | None:
        return None if self.budget is None else self.budget - self.spent

    @property
    def state(self) -> BudgetState:
        if self.budget is None:
            return BudgetState.NO_BUDGET
        if self.spent > self.budget:
            return BudgetState.OVER
        if self.spent + self.awaiting > self.budget:
            return BudgetState.AT_RISK
        return BudgetState.OK


def category_usage(
    categories: Sequence[CategoryBudget], expenses: Iterable[ExpenseRecord], period: BudgetPeriod | None
) -> list[CategoryUsage]:
    """계정과목마다 집행액·승인 대기·잔액 (계정과목 순서 그대로). 계정과목이 없는 품목은 안 셈"""
    spent: dict[int, int] = defaultdict(int)
    awaiting: dict[int, int] = defaultdict(int)
    for expense in expenses:
        if not in_period(expense, period):
            continue
        if expense.status == ExpenseStatus.APPROVED:
            target = spent
        elif expense.status == ExpenseStatus.SUBMITTED:
            target = awaiting
        else:
            continue
        for item in expense.items:
            if item.category_id is not None:
                target[item.category_id] += item.amount
    return [
        CategoryUsage(category_id=c.id, budget=c.budget, spent=spent[c.id], awaiting=awaiting[c.id]) for c in categories
    ]


@dataclass(frozen=True)
class UsageTotals:
    budget: int | None  # 예산을 정한 계정과목의 예산 합. 하나도 없으면 None
    spent: int  # 모든 계정과목 집행액 합
    awaiting: int


def usage_totals(usages: Iterable[CategoryUsage]) -> UsageTotals:
    usages = list(usages)
    budgets = [u.budget for u in usages if u.budget is not None]
    return UsageTotals(
        budget=sum(budgets) if budgets else None,
        spent=sum(u.spent for u in usages),
        awaiting=sum(u.awaiting for u in usages),
    )


@dataclass(frozen=True)
class BudgetWarning:
    category_id: int
    budget: int
    spent: int  # 이 지출을 빼고 이미 승인된 집행액
    this_amount: int  # 이 지출에서 그 계정과목 금액
    over_by: int  # 승인하면 넘는 금액


def approval_warnings(
    expense: ExpenseRecord,
    categories: Sequence[CategoryBudget],
    expenses: Iterable[ExpenseRecord],
    period: BudgetPeriod | None,
) -> list[BudgetWarning]:
    """이 지출을 승인하면 예산을 넘게 되는 계정과목 (예산 기간 밖 결제면 예산과 무관 → 없음)"""
    if not in_period(expense, period):
        return []
    this_by_category: dict[int, int] = defaultdict(int)
    for item in expense.items:
        if item.category_id is not None:
            this_by_category[item.category_id] += item.amount
    others = [e for e in expenses if e.id != expense.id]
    usage = {u.category_id: u for u in category_usage(categories, others, period)}
    warnings = []
    for category in categories:
        amount = this_by_category.get(category.id)
        current = usage[category.id]
        if amount is None or amount <= 0 or current.budget is None:  # 할인만 있는 계정은 늘지 않음
            continue
        after = current.spent + amount
        if after > current.budget:
            warnings.append(
                BudgetWarning(
                    category_id=category.id,
                    budget=current.budget,
                    spent=current.spent,
                    this_amount=amount,
                    over_by=after - current.budget,
                )
            )
    return warnings
