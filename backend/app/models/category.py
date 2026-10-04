from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import StrictInteger
from app.models.common import TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class Category(TimestampMixin, Base):
    """계정과목 겸 예산 항목 (조직별)."""

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("organization_id", "name"),
        CheckConstraint("budget_amount IS NULL OR budget_amount >= 0", name="budget_amount_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(50))
    # 원 단위 정수. NULL = 예산 미설정
    budget_amount: Mapped[int | None] = mapped_column(StrictInteger)

    organization: Mapped["Organization"] = relationship(back_populates="categories")
