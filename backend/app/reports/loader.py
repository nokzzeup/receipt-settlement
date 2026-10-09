"""DB → 리포트 입력 (승인 대기·승인된 지출 + 품목 + 사람 이름 + 승인 시각). 계산은 summary.py"""

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.models import ApprovalAction, ApprovalLog, Expense, ExpenseItem, ExpenseStatus, Membership, Receipt, User
from app.reports.summary import ReportExpense, ReportItem

_STATUSES = (ExpenseStatus.SUBMITTED, ExpenseStatus.APPROVED)


def load_report_expenses(db: Session, organization_id: int) -> list[ReportExpense]:
    payer, payer_user = aliased(Membership), aliased(User)
    uploader, uploader_user = aliased(Membership), aliased(User)
    rows = db.execute(
        select(
            Expense.id,
            Expense.status,
            Expense.payer_membership_id,
            Expense.reimbursed_at,
            Receipt.store_name,
            Receipt.paid_at,
            payer_user.name,
            uploader_user.name,
        )
        .join(Receipt, Receipt.id == Expense.receipt_id)
        .join(payer, payer.id == Expense.payer_membership_id)
        .join(payer_user, payer_user.id == payer.user_id)
        .join(uploader, uploader.id == Receipt.uploader_membership_id)
        .join(uploader_user, uploader_user.id == uploader.user_id)
        .where(Expense.organization_id == organization_id, Expense.status.in_(_STATUSES))
    ).all()

    items: dict[int, list[ReportItem]] = defaultdict(list)
    for expense_id, name, quantity, unit_price, amount, category_id in db.execute(
        select(
            ExpenseItem.expense_id,
            ExpenseItem.name,
            ExpenseItem.quantity,
            ExpenseItem.unit_price,
            ExpenseItem.amount,
            ExpenseItem.category_id,
        )
        .join(Expense, Expense.id == ExpenseItem.expense_id)
        .where(Expense.organization_id == organization_id, Expense.status.in_(_STATUSES))
        .order_by(ExpenseItem.id)
    ):
        items[expense_id].append(
            ReportItem(name=name, quantity=quantity, unit_price=unit_price, amount=amount, category_id=category_id)
        )

    approved_at = dict(
        db.execute(
            select(ApprovalLog.expense_id, func.max(ApprovalLog.created_at))
            .join(Expense, Expense.id == ApprovalLog.expense_id)
            .where(Expense.organization_id == organization_id, ApprovalLog.action == ApprovalAction.APPROVE)
            .group_by(ApprovalLog.expense_id)
        ).all()
    )

    return [
        ReportExpense(
            id=row[0],
            status=row[1],
            payer_id=row[2],
            reimbursed_at=row[3],
            store_name=row[4],
            paid_at=row[5],
            payer_name=row[6],
            uploader_name=row[7],
            approved_at=approved_at.get(row[0]),
            items=tuple(items[row[0]]),
        )
        for row in rows
    ]
