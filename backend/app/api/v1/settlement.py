"""정산: 결제자별 돌려줄 돈, 계정별 예산 사용, 한 번에 환급 완료 표시.

계산 규칙은 app/settlement/engine.py (pytest로 고정). 여기서는 범위(누가 무엇을 보나)만 정한다.
- 총무·승인자: 조직 전체 결제자. 구성원: 내 몫만 (다른 사람이 얼마 받는지는 안 보임)
- 계정별 예산 사용은 구성원 누구나 조직 전체로 (예산 집행은 공개가 기본이라서)
- '보냈어요'(한 번에 환급 완료): 총무만
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, DbSession, TreasurerMembership
from app.models import ApprovalAction, ApprovalLog, Expense, ExpenseStatus, Membership, MembershipRole, Organization, Receipt, User
from app.schemas.expense import PersonOut
from app.schemas.settlement import (
    BudgetPeriodOut,
    BulkReimburseRequest,
    BulkReimburseResult,
    CategoryUsageOut,
    PayerBalanceOut,
    ReimbursableExpense,
    SettlementOut,
)
from app.settlement import (
    PayerBalance,
    budget_period,
    category_budgets,
    category_usage,
    load_categories,
    load_expense_records,
    payer_balances,
    usage_totals,
)

router = APIRouter(prefix="/orgs/{org_id}/settlement", tags=["settlement"])

_ORG_SCOPE_ROLES = {MembershipRole.TREASURER, MembershipRole.APPROVER}


def _people(db: DbSession, org_id: int) -> dict[int, str]:
    rows = db.execute(
        select(Membership.id, User.name).join(User, User.id == Membership.user_id).where(Membership.organization_id == org_id)
    )
    return {membership_id: name for membership_id, name in rows}


def _receipts(db: DbSession, expense_ids: Sequence[int]) -> dict[int, tuple[str | None, datetime | None]]:
    if not expense_ids:
        return {}
    rows = db.execute(
        select(Expense.id, Receipt.store_name, Receipt.paid_at)
        .join(Receipt, Receipt.id == Expense.receipt_id)
        .where(Expense.id.in_(expense_ids))
    )
    return {expense_id: (store_name, paid_at) for expense_id, store_name, paid_at in rows}


@router.get("")
def get_settlement(org_id: int, me: CurrentMembership, db: DbSession) -> SettlementOut:
    org = db.get_one(Organization, org_id)
    records = load_expense_records(db, org_id)
    amounts = {r.id: r.amount for r in records}
    balances = payer_balances(records)
    org_scope = me.role in _ORG_SCOPE_ROLES
    visible = balances if org_scope else [b for b in balances if b.payer_id == me.id]

    people = _people(db, org_id)
    receipts = _receipts(db, [i for b in visible for i in b.reimbursable_ids])

    def payer_out(balance: PayerBalance) -> PayerBalanceOut:
        return PayerBalanceOut(
            payer=PersonOut(membership_id=balance.payer_id, name=people.get(balance.payer_id, "(알 수 없음)")),
            to_reimburse=balance.to_reimburse,
            expenses=[
                ReimbursableExpense(
                    id=expense_id,
                    store_name=receipts[expense_id][0],
                    paid_at=receipts[expense_id][1],
                    amount=amounts[expense_id],
                )
                for expense_id in balance.reimbursable_ids
            ],
            awaiting_approval=balance.awaiting_approval,
            awaiting_count=balance.awaiting_count,
        )

    payers = [payer_out(b) for b in visible]
    mine = next((p for p in payers if p.payer.membership_id == me.id), None)
    if mine is None:
        mine = PayerBalanceOut(
            payer=PersonOut(membership_id=me.id, name=people[me.id]),
            to_reimburse=0,
            expenses=[],
            awaiting_approval=0,
            awaiting_count=0,
        )

    categories = load_categories(db, org_id)
    period = budget_period(org)
    usages = category_usage(category_budgets(categories), records, period)
    names = {c.id: c.name for c in categories}
    totals = usage_totals(usages)
    return SettlementOut(
        scope="org" if org_scope else "me",
        to_reimburse=sum(p.to_reimburse for p in payers),
        to_reimburse_count=sum(len(p.expenses) for p in payers),
        awaiting_approval=sum(p.awaiting_approval for p in payers),
        awaiting_count=sum(p.awaiting_count for p in payers),
        payers=payers,
        me=mine,
        period=BudgetPeriodOut(start=period.start, end=period.end) if period else None,
        categories=[
            CategoryUsageOut(
                category_id=u.category_id,
                name=names[u.category_id],
                budget=u.budget,
                spent=u.spent,
                awaiting=u.awaiting,
                remaining=u.remaining,
                state=u.state,
            )
            for u in usages
        ],
        budget_total=totals.budget,
        spent_total=totals.spent,
        awaiting_total=totals.awaiting,
    )


@router.post("/reimburse")
def reimburse_payer(
    org_id: int, body: BulkReimburseRequest, me: TreasurerMembership, db: DbSession
) -> BulkReimburseResult:
    """결제자 한 명에게 보낸 것으로 한 번에 표시 (총무). 목록 중 하나라도 그 사이 바뀌었으면 아무것도 안 바꾸고 409"""
    ids = set(body.expense_ids)
    expenses = list(
        db.scalars(select(Expense).where(Expense.organization_id == org_id, Expense.id.in_(ids)).order_by(Expense.id))
    )
    if len(expenses) != len(ids) or any(
        e.payer_membership_id != body.payer_membership_id
        or e.status != ExpenseStatus.APPROVED
        or e.reimbursed_at is not None
        for e in expenses
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "그 사이에 바뀐 지출이 있어요. 화면을 새로고침한 뒤 다시 확인하세요."
        )
    now = datetime.now(UTC)
    for expense in expenses:
        expense.reimbursed_at = now
        expense.reimbursed_by_membership_id = me.id
        expense.approval_logs.append(ApprovalLog(actor_membership_id=me.id, action=ApprovalAction.REIMBURSE))
    amount = sum(item.amount for e in expenses for item in e.items)
    db.commit()
    return BulkReimburseResult(count=len(expenses), amount=amount)
