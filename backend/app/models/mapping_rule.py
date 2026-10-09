from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin

if TYPE_CHECKING:
    from app.models.category import Category


class MappingRule(TimestampMixin, Base):
    """품목명 키워드 → 계정과목 매핑 규칙.

    지금 쓰는 것은 조직 규칙뿐이다 (4단계 결정): organization_id + category_id, keyword = 정규화한 품목명.
    제출할 때 사용자가 직접 고른 품목으로 생성·hit_count 증가 (app/classify/classifier.py).
    기본(전역) 규칙은 코드(app/classify/defaults.py)에 둔다 — 아래 전역 규칙 칸은 예비로 남겨둔 것.

    두 종류가 한 테이블에 들어갈 수 있게 되어 있다 (CHECK 제약으로 강제):
    - 조직 규칙  : organization_id + category_id
    - 전역 규칙  : organization_id = NULL + category_name (계정과목 이름으로 매칭, 지금은 안 씀)

    유니크 제약 2개는 NULL을 서로 다른 값으로 취급하는 특성 때문에
    첫 번째는 조직 규칙에만, 두 번째는 전역 규칙에만 실제로 적용된다.
    키워드 하나가 여러 계정과목을 가질 수 있게 열어둠 (hit_count 비교로 고르는 방식 가능)
    """

    __tablename__ = "mapping_rules"
    __table_args__ = (
        CheckConstraint(
            "(organization_id IS NOT NULL AND category_id IS NOT NULL AND category_name IS NULL)"
            " OR (organization_id IS NULL AND category_id IS NULL AND category_name IS NOT NULL)",
            name="org_rule_or_global_rule",
        ),
        UniqueConstraint("organization_id", "keyword", "category_id"),
        UniqueConstraint("keyword", "category_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"))
    keyword: Mapped[str] = mapped_column(String(100))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    category_name: Mapped[str | None] = mapped_column(String(50))
    hit_count: Mapped[int] = mapped_column(default=0, server_default="0")

    category: Mapped["Category | None"] = relationship()
