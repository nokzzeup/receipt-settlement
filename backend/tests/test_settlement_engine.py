"""정산 엔진 단위 테스트 — 돌려줄 돈, 계정별 집행액·잔액, 예산 기간, 승인 경고 (금액은 int만)"""

from datetime import UTC, date, datetime

import pytest

from app.core.timezone import KST
from app.models.enums import ExpenseStatus
from app.settlement import (
    BudgetPeriod,
    BudgetState,
    CategoryBudget,
    ExpenseRecord,
    ItemLine,
    approval_warnings,
    category_usage,
    payer_balances,
    usage_totals,
)

FOOD, SNACK, OFFICE = 1, 2, 3
ALICE, BOB, CAROL = 10, 20, 30
SEMESTER = BudgetPeriod(start=date(2026, 9, 1), end=date(2026, 12, 31))


def record(
    id: int,
    payer: int = ALICE,
    status: ExpenseStatus = ExpenseStatus.APPROVED,
    reimbursed: bool = False,
    paid_at: datetime | None = datetime(2026, 10, 1, 12, 0, tzinfo=KST),
    items: tuple[tuple[int | None, int], ...] = ((FOOD, 10_000),),
) -> ExpenseRecord:
    return ExpenseRecord(
        id=id,
        payer_id=payer,
        status=status,
        reimbursed=reimbursed,
        paid_at=paid_at,
        items=tuple(ItemLine(category_id=c, amount=a) for c, a in items),
    )


# ---------- 돌려줄 돈 ----------


def test_payer_balances_count_only_approved_and_not_reimbursed() -> None:
    expenses = [
        record(1, ALICE, items=((FOOD, 10_000), (SNACK, 2_500))),
        record(2, ALICE, items=((FOOD, 8_000), (FOOD, -1_000))),  # 할인 줄은 빼고 셈
        record(3, ALICE, reimbursed=True, items=((FOOD, 99_000),)),  # 이미 돌려줌
        record(4, BOB, status=ExpenseStatus.SUBMITTED, items=((SNACK, 4_000),)),  # 승인 대기
        record(5, BOB, items=((OFFICE, 3_000),)),
        record(6, CAROL, status=ExpenseStatus.DRAFT, items=((FOOD, 50_000),)),  # 작성 중 → 안 셈
        record(7, CAROL, status=ExpenseStatus.REJECTED, items=((FOOD, 50_000),)),  # 반려 → 안 셈
    ]
    balances = payer_balances(expenses)

    assert [(b.payer_id, b.to_reimburse, b.reimbursable_ids, b.awaiting_approval, b.awaiting_count) for b in balances] == [
        (ALICE, 19_500, (1, 2), 0, 0),
        (BOB, 3_000, (5,), 4_000, 1),
    ]
    assert all(isinstance(b.to_reimburse, int) for b in balances)


def test_payer_balances_ignore_budget_period_and_sort() -> None:
    last_year = datetime(2025, 3, 2, 9, 0, tzinfo=KST)
    expenses = [
        record(1, BOB, paid_at=last_year, items=((FOOD, 5_000),)),  # 지난 기간이어도 안 돌려줬으면 대상
        record(2, ALICE, items=((FOOD, 5_000),)),
        record(3, CAROL, status=ExpenseStatus.SUBMITTED, items=((FOOD, 7_000),)),
        record(4, ALICE, paid_at=datetime(2026, 9, 2, tzinfo=KST), items=((FOOD, 1_000),)),
    ]
    balances = payer_balances(expenses)
    # 돌려줄 돈 같으면 승인 대기 많은 순 → id 순. 돌려줄 돈 0이고 대기만 있는 사람은 뒤로
    assert [(b.payer_id, b.to_reimburse) for b in balances] == [(ALICE, 6_000), (BOB, 5_000), (CAROL, 0)]
    # 지출 목록은 결제일 순
    assert balances[0].reimbursable_ids == (4, 2)
    assert payer_balances([]) == []


# ---------- 계정별 집행액·잔액 ----------


def test_category_usage_spent_awaiting_and_states() -> None:
    categories = [CategoryBudget(FOOD, 30_000), CategoryBudget(SNACK, 10_000), CategoryBudget(OFFICE, None)]
    expenses = [
        record(1, items=((FOOD, 20_000), (SNACK, 6_000))),
        record(2, reimbursed=True, items=((FOOD, 15_000),)),  # 돌려줬어도 집행액
        record(3, status=ExpenseStatus.SUBMITTED, items=((SNACK, 5_000), (OFFICE, 2_000))),
        record(4, status=ExpenseStatus.DRAFT, items=((SNACK, 100_000),)),
        record(5, items=((None, 1_000), (OFFICE, 3_000), (OFFICE, -500))),
    ]
    usage = {u.category_id: u for u in category_usage(categories, expenses, period=None)}

    food, snack, office = usage[FOOD], usage[SNACK], usage[OFFICE]
    assert (food.spent, food.awaiting, food.remaining, food.state) == (35_000, 0, -5_000, BudgetState.OVER)
    assert (snack.spent, snack.awaiting, snack.remaining, snack.state) == (6_000, 5_000, 4_000, BudgetState.AT_RISK)
    assert (office.spent, office.awaiting, office.remaining, office.state) == (2_500, 2_000, None, BudgetState.NO_BUDGET)
    # 계정과목 순서 그대로
    assert [u.category_id for u in category_usage(categories, expenses, None)] == [FOOD, SNACK, OFFICE]

    totals = usage_totals(usage.values())
    assert (totals.budget, totals.spent, totals.awaiting) == (40_000, 43_500, 7_000)
    assert usage_totals(category_usage([CategoryBudget(FOOD, None)], [], None)).budget is None


def test_budget_exactly_used_is_ok_and_zero_budget() -> None:
    usage = category_usage([CategoryBudget(FOOD, 10_000)], [record(1, items=((FOOD, 10_000),))], None)[0]
    assert (usage.remaining, usage.state) == (0, BudgetState.OK)

    zero = category_usage(
        [CategoryBudget(FOOD, 0)], [record(1, status=ExpenseStatus.SUBMITTED, items=((FOOD, 1),))], None
    )[0]
    assert zero.state == BudgetState.AT_RISK


@pytest.mark.parametrize(
    ("paid_at", "counted"),
    [
        (datetime(2026, 9, 1, 0, 0, tzinfo=KST), True),  # 시작일 0시
        (datetime(2026, 12, 31, 23, 59, tzinfo=KST), True),  # 마지막 날 밤
        (datetime(2027, 1, 1, 0, 0, tzinfo=KST), False),
        (None, False),  # 결제일 모름 → 기간 밖
    ],
)
def test_budget_period_uses_korean_date(paid_at: datetime | None, counted: bool) -> None:
    usage = category_usage([CategoryBudget(FOOD, 1)], [record(1, paid_at=paid_at, items=((FOOD, 700),))], SEMESTER)[0]
    assert usage.spent == (700 if counted else 0)


def test_budget_period_boundary_in_utc() -> None:
    # UTC 8월 31일 15:30 = 한국 9월 1일 00:30 → 기간 안
    inside = datetime(2026, 8, 31, 15, 30, tzinfo=UTC)
    # UTC 12월 31일 15:00 = 한국 1월 1일 00:00 → 기간 밖
    outside = datetime(2026, 12, 31, 15, 0, tzinfo=UTC)
    expenses = [record(1, paid_at=inside, items=((FOOD, 100),)), record(2, paid_at=outside, items=((FOOD, 1_000),))]
    assert category_usage([CategoryBudget(FOOD, None)], expenses, SEMESTER)[0].spent == 100
    assert category_usage([CategoryBudget(FOOD, None)], expenses, None)[0].spent == 1_100  # 기간 없음 = 전체


# ---------- 승인 경고 ----------


def test_approval_warnings_when_approving_would_exceed_budget() -> None:
    categories = [CategoryBudget(FOOD, 30_000), CategoryBudget(SNACK, 10_000), CategoryBudget(OFFICE, None)]
    approved = record(1, items=((FOOD, 25_000), (SNACK, 9_000)))
    other_pending = record(2, status=ExpenseStatus.SUBMITTED, items=((FOOD, 50_000),))  # 다른 대기 건은 안 셈
    target = record(
        3,
        status=ExpenseStatus.SUBMITTED,
        items=((FOOD, 4_000), (FOOD, 3_000), (SNACK, 1_000), (OFFICE, 99_000)),
    )
    warnings = approval_warnings(target, categories, [approved, other_pending, target], period=None)

    # 식비: 25,000 + 7,000 = 32,000 > 30,000 → 2,000 넘음. 간식: 9,000 + 1,000 = 예산과 같음 → 경고 없음. 비품: 예산 없음
    assert [(w.category_id, w.budget, w.spent, w.this_amount, w.over_by) for w in warnings] == [
        (FOOD, 30_000, 25_000, 7_000, 2_000)
    ]


def test_approval_warnings_outside_period_or_discount_only() -> None:
    categories = [CategoryBudget(FOOD, 1_000)]
    approved = record(1, items=((FOOD, 5_000),))  # 이미 넘음
    last_year = record(2, status=ExpenseStatus.SUBMITTED, paid_at=datetime(2025, 5, 1, tzinfo=KST), items=((FOOD, 9_000),))
    assert approval_warnings(last_year, categories, [approved, last_year], SEMESTER) == []

    discount = record(3, status=ExpenseStatus.SUBMITTED, items=((FOOD, -500),))
    assert approval_warnings(discount, categories, [approved, discount], SEMESTER) == []
