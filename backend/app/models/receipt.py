from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import StrictInteger
from app.models.common import TimestampMixin

if TYPE_CHECKING:
    from app.models.expense import Expense
    from app.models.organization import Membership


class Receipt(TimestampMixin, Base):
    """업로드된 영수증 원본 + OCR 결과.

    store_name / paid_at / total_amount 는 '영수증에 찍힌 값'(확인·수정 후)이다.
    실제 환급 금액은 Expense의 품목 합계로 계산한다 (개인 지출 품목을 빼면 둘이 달라질 수 있음).
    """

    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    uploader_membership_id: Mapped[int] = mapped_column(ForeignKey("memberships.id"))
    # settings.storage_path 기준 상대경로
    image_path: Mapped[str] = mapped_column(String(500))
    # 중복 감지용 해시. 알고리즘(정확 일치 sha256 / 유사도 pHash)은 6단계에서 결정 → 64자면 둘 다 수용
    image_hash: Mapped[str] = mapped_column(String(64), index=True)
    # OcrRawResult JSON. 저장 전에 카드번호 패턴을 반드시 마스킹할 것
    ocr_raw: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    store_name: Mapped[str | None] = mapped_column(String(200))
    paid_at: Mapped[datetime | None]
    total_amount: Mapped[int | None] = mapped_column(StrictInteger)

    uploader: Mapped["Membership"] = relationship()
    expense: Mapped["Expense | None"] = relationship(back_populates="receipt")
