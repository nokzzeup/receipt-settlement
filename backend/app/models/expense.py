from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import StrictInteger
from app.models.common import TimestampMixin, str_enum
from app.models.enums import CategorySource, ExpenseStatus

if TYPE_CHECKING:
    from app.models.approval_log import ApprovalLog
    from app.models.category import Category
    from app.models.organization import Membership
    from app.models.receipt import Receipt


class Expense(TimestampMixin, Base):
    """지출 1건 = 영수증 1장. 결제자(payer)가 환급받을 사람.

    - 지출 금액은 컬럼으로 저장하지 않고 items.amount 합계로 계산한다 (값이 두 군데 있으면 어긋남)
    - 환급 완료(reimbursed_*)는 APPROVED 상태에서만 가능 → DB CHECK 제약으로도 막아둠
    - 같은 조직 데이터끼리만 연결되는지(영수증·결제자·계정과목)는 DB가 보장하지 않으므로 서비스 계층에서 검증할 것
    """

    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint(
            "(reimbursed_at IS NULL) = (reimbursed_by_membership_id IS NULL)",
            name="reimbursed_fields_together",
        ),
        CheckConstraint(
            "reimbursed_at IS NULL OR status = 'APPROVED'",
            name="reimbursed_only_when_approved",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), unique=True)
    payer_membership_id: Mapped[int] = mapped_column(ForeignKey("memberships.id"), index=True)
    status: Mapped[ExpenseStatus] = mapped_column(
        str_enum(ExpenseStatus, "expense_status"),
        default=ExpenseStatus.DRAFT,
        server_default=ExpenseStatus.DRAFT.value,
    )
    reject_reason: Mapped[str | None] = mapped_column(Text)
    reimbursed_at: Mapped[datetime | None]
    reimbursed_by_membership_id: Mapped[int | None] = mapped_column(ForeignKey("memberships.id"))

    receipt: Mapped["Receipt"] = relationship(back_populates="expense")
    payer: Mapped["Membership"] = relationship(foreign_keys=[payer_membership_id])
    reimbursed_by: Mapped["Membership | None"] = relationship(foreign_keys=[reimbursed_by_membership_id])
    items: Mapped[list["ExpenseItem"]] = relationship(
        back_populates="expense", cascade="all, delete-orphan", order_by="ExpenseItem.id"
    )
    approval_logs: Mapped[list["ApprovalLog"]] = relationship(
        back_populates="expense", cascade="all, delete-orphan", order_by="ApprovalLog.created_at"
    )


class ExpenseItem(TimestampMixin, Base):
    """품목 1줄. 계정과목 분류·예산 집행액·환급 금액 계산의 최소 단위."""

    __tablename__ = "expense_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(StrictInteger, default=1, server_default="1")
    unit_price: Mapped[int | None] = mapped_column(StrictInteger)  # 영수증에 단가가 없으면 NULL
    amount: Mapped[int] = mapped_column(StrictInteger)  # 이 품목의 금액(원). 집계는 항상 이 값 기준
    # NULL = 미분류
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    category_source: Mapped[CategorySource | None] = mapped_column(
        str_enum(CategorySource, "category_source")
    )

    expense: Mapped["Expense"] = relationship(back_populates="items")
    category: Mapped["Category | None"] = relationship()
