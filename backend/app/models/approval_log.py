from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import str_enum
from app.models.enums import ApprovalAction

if TYPE_CHECKING:
    from app.models.expense import Expense
    from app.models.organization import Membership


class ApprovalLog(Base):
    """제출·승인·반려·환급 이력 (수정하지 않고 쌓기만 함)."""

    __tablename__ = "approval_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"), index=True)
    actor_membership_id: Mapped[int] = mapped_column(ForeignKey("memberships.id"))
    action: Mapped[ApprovalAction] = mapped_column(str_enum(ApprovalAction, "approval_action"))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    expense: Mapped["Expense"] = relationship(back_populates="approval_logs")
    actor: Mapped["Membership"] = relationship()
