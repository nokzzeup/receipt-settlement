from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, str_enum
from app.models.enums import MembershipRole

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "(budget_period_start IS NULL) = (budget_period_end IS NULL)", name="budget_period_together"
        ),
        CheckConstraint(
            "budget_period_start IS NULL OR budget_period_start <= budget_period_end", name="budget_period_order"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # 재발급 = 값 교체 (이전 코드는 즉시 무효)
    invite_code: Mapped[str] = mapped_column(String(16), unique=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # 지금 예산 기간 (한국 날짜, 양 끝 포함). 계정별 집행액·잔액은 결제일이 이 안인 지출만 센다.
    # 둘 다 NULL = 기간 없음(전체 누적). 새 학기엔 총무가 바꾼다. 돌려줄 돈은 기간과 상관없이 전부
    budget_period_start: Mapped[date | None]
    budget_period_end: Mapped[date | None]

    created_by: Mapped["User"] = relationship()
    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")
    categories: Mapped[list["Category"]] = relationship(back_populates="organization")


class Membership(TimestampMixin, Base):
    """조직 구성원 + 역할. 서버 권한 체크의 기준.

    결제자·업로더·승인 처리자·환급 처리자는 모두 User가 아니라 Membership을 가리킨다.
    (컬럼 이름도 *_membership_id 로 통일 → user.id 를 잘못 넣는 실수 방지)
    """

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[MembershipRole] = mapped_column(
        str_enum(MembershipRole, "membership_role"), default=MembershipRole.MEMBER
    )

    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")
