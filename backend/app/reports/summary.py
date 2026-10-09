"""기간별 리포트 계산 (순수 함수, tests/test_reports.py).

리포트 = 기간 안에 결제한(한국 날짜, 양 끝 포함) **승인된** 지출. 승인 대기는 합계에 넣지 않고 따로 알려준다.
금액은 int만 (품목 금액 합, 할인 줄 포함).
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from app.core.timezone import KST
from app.models.enums import ExpenseStatus


@dataclass(frozen=True)
class ReportItem:
    name: str
    quantity: int
    unit_price: int | None
    amount: int
    category_id: int | None


@dataclass(frozen=True)
class ReportExpense:
    id: int
    status: ExpenseStatus
    store_name: str | None
    paid_at: datetime | None
    payer_id: int
    payer_name: str
    uploader_name: str
    approved_at: datetime | None  # 마지막 승인 시각
    reimbursed_at: datetime | None
    items: tuple[ReportItem, ...]

    @property
    def amount(self) -> int:
        return sum(item.amount for item in self.items)


def in_range(paid_at: datetime | None, start: date, end: date) -> bool:
    return paid_at is not None and start <= paid_at.astimezone(KST).date() <= end


@dataclass(frozen=True)
class CategoryTotal:
    category_id: int | None  # None = 미분류 (승인된 지출엔 보통 없음)
    amount: int
    item_count: int


@dataclass(frozen=True)
class PayerTotal:
    payer_id: int
    payer_name: str
    amount: int  # 승인된 금액
    reimbursed: int  # 그중 돌려준 금액
    expense_count: int

    @property
    def unreimbursed(self) -> int:
        return self.amount - self.reimbursed


@dataclass(frozen=True)
class ReportSummary:
    start: date
    end: date
    expenses: tuple[ReportExpense, ...]  # 기간 안 승인된 지출 (결제일 순)
    approved_amount: int
    reimbursed_amount: int
    categories: tuple[CategoryTotal, ...]  # 금액 큰 순
    payers: tuple[PayerTotal, ...]  # 금액 큰 순
    awaiting_count: int  # 기간 안 승인 대기 (합계에 안 들어감)
    awaiting_amount: int

    @property
    def unreimbursed_amount(self) -> int:
        return self.approved_amount - self.reimbursed_amount


def summarize(expenses: Iterable[ReportExpense], start: date, end: date) -> ReportSummary:
    in_period = [e for e in expenses if in_range(e.paid_at, start, end)]
    approved = sorted(
        (e for e in in_period if e.status == ExpenseStatus.APPROVED),
        key=lambda e: (e.paid_at, e.id),
    )
    awaiting = [e for e in in_period if e.status == ExpenseStatus.SUBMITTED]

    by_category: dict[int | None, list[int]] = defaultdict(lambda: [0, 0])
    for expense in approved:
        for item in expense.items:
            total = by_category[item.category_id]
            total[0] += item.amount
            total[1] += 1

    by_payer: dict[int, list[ReportExpense]] = defaultdict(list)
    for expense in approved:
        by_payer[expense.payer_id].append(expense)

    categories = sorted(
        (CategoryTotal(category_id=cid, amount=amount, item_count=count) for cid, (amount, count) in by_category.items()),
        key=lambda c: (-c.amount, c.category_id is None, c.category_id or 0),
    )
    payers = sorted(
        (
            PayerTotal(
                payer_id=payer_id,
                payer_name=mine[0].payer_name,
                amount=sum(e.amount for e in mine),
                reimbursed=sum(e.amount for e in mine if e.reimbursed_at is not None),
                expense_count=len(mine),
            )
            for payer_id, mine in by_payer.items()
        ),
        key=lambda p: (-p.amount, p.payer_id),
    )
    return ReportSummary(
        start=start,
        end=end,
        expenses=tuple(approved),
        approved_amount=sum(e.amount for e in approved),
        reimbursed_amount=sum(e.amount for e in approved if e.reimbursed_at is not None),
        categories=tuple(categories),
        payers=tuple(payers),
        awaiting_count=len(awaiting),
        awaiting_amount=sum(e.amount for e in awaiting),
    )
