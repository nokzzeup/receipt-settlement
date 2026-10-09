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
    # 중복 감지 (app/receipts/duplicates.py)
    # - image_hash: 파일 sha256 → 완전히 같은 파일
    # - image_phash: 사진 지문(256비트 dHash, 16진수 64자) → 다시 저장·크기 조절·메신저로 보낸 같은 사진.
    #   사진을 못 읽으면 NULL (6단계 전에 올린 영수증도 NULL → 같은 파일·같은 내용으로만 비교)
    image_hash: Mapped[str] = mapped_column(String(64), index=True)
    image_phash: Mapped[str | None] = mapped_column(String(64))
    # OcrRawResult JSON. 저장 전에 카드번호 패턴을 반드시 마스킹할 것
    ocr_raw: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    store_name: Mapped[str | None] = mapped_column(String(200))
    paid_at: Mapped[datetime | None]
    total_amount: Mapped[int | None] = mapped_column(StrictInteger)

    uploader: Mapped["Membership"] = relationship()
    expense: Mapped["Expense | None"] = relationship(back_populates="receipt")
