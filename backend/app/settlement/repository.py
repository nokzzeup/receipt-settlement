"""DB → 정산 엔진 입력(ExpenseRecord 등). 계산은 engine.py, 여기는 읽기만."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Expense, ExpenseItem, ExpenseStatus, Organization, Receipt
from app.settlement.engine import BudgetPeriod, CategoryBudget, ExpenseRecord, ItemLine

# 정산에 쓰는 상태 (작성 중·반려는 어디에도 안 셈)
COUNTED_STATUSES = (ExpenseStatus.SUBMITTED, ExpenseStatus.APPROVED)


def load_expense_records(db: Session, organization_id: int) -> list[ExpenseRecord]:
    """조직의 승인 대기·승인된 지출 전부 (동아리 규모 → 한 번에 읽어서 계산)"""
    rows = db.execute(
        select(Expense.id, Expense.payer_membership_id, Expense.status, Expense.reimbursed_at, Receipt.paid_at)
        .join(Receipt, Receipt.id == Expense.receipt_id)
        .where(Expense.organization_id == organization_id, Expense.status.in_(COUNTED_STATUSES))
    ).all()
    items: dict[int, list[ItemLine]] = defaultdict(list)
    for expense_id, category_id, amount in db.execute(
        select(ExpenseItem.expense_id, ExpenseItem.category_id, ExpenseItem.amount)
        .join(Expense, Expense.id == ExpenseItem.expense_id)
        .where(Expense.organization_id == organization_id, Expense.status.in_(COUNTED_STATUSES))
        .order_by(ExpenseItem.id)
    ):
        items[expense_id].append(ItemLine(category_id=category_id, amount=amount))
    return [
        ExpenseRecord(
            id=row.id,
            payer_id=row.payer_membership_id,
            status=row.status,
            reimbursed=row.reimbursed_at is not None,
            paid_at=row.paid_at,
            items=tuple(items[row.id]),
        )
        for row in rows
    ]


def load_categories(db: Session, organization_id: int) -> list[Category]:
    return list(db.scalars(select(Category).where(Category.organization_id == organization_id).order_by(Category.id)))


def category_budgets(categories: list[Category]) -> list[CategoryBudget]:
    return [CategoryBudget(id=c.id, budget=c.budget_amount) for c in categories]


def budget_period(org: Organization) -> BudgetPeriod | None:
    if org.budget_period_start is None or org.budget_period_end is None:
        return None
    return BudgetPeriod(start=org.budget_period_start, end=org.budget_period_end)
