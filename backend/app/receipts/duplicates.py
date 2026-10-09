"""중복 영수증 감지 — 막지 않고 경고만 한다 (같은 가게에서 같은 금액을 두 번 살 수도 있으므로).

같은 조직의 다른 영수증 중에서 (강한 근거 순)
1. SAME_IMAGE    파일이 완전히 같음 (sha256)
2. SIMILAR_IMAGE 사진 지문이 가까움 (다시 저장·메신저로 받은 같은 사진, fingerprint.py)
3. SAME_DETAILS  가게 이름(띄어쓰기·대소문자 무시) + 결제일시(분 단위) + 영수증 합계가 같음 (다시 찍은 사진)
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Receipt
from app.receipts.fingerprint import SIMILAR_MAX_DISTANCE, hamming_distance

MAX_RESULTS = 5


class DuplicateReason(StrEnum):
    SAME_IMAGE = "SAME_IMAGE"
    SIMILAR_IMAGE = "SIMILAR_IMAGE"
    SAME_DETAILS = "SAME_DETAILS"


_STRENGTH = {DuplicateReason.SAME_IMAGE: 0, DuplicateReason.SIMILAR_IMAGE: 1, DuplicateReason.SAME_DETAILS: 2}
_NOT_KEY = re.compile(r"[^0-9a-z가-힣]")


@dataclass(frozen=True)
class DuplicateMatch:
    receipt: Receipt
    reason: DuplicateReason


def store_key(name: str | None) -> str:
    return _NOT_KEY.sub("", unicodedata.normalize("NFKC", name or "").lower())


def _minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def find_duplicates(db: Session, receipt: Receipt) -> list[DuplicateMatch]:
    """이 영수증과 같아 보이는 같은 조직의 다른 영수증 (강한 근거 → 최근 것 순, 최대 5개)"""
    others = select(Receipt).where(Receipt.organization_id == receipt.organization_id, Receipt.id != receipt.id)
    found: dict[int, DuplicateMatch] = {}

    def add(other: Receipt, reason: DuplicateReason) -> None:
        current = found.get(other.id)
        if current is None or _STRENGTH[reason] < _STRENGTH[current.reason]:
            found[other.id] = DuplicateMatch(receipt=other, reason=reason)

    for other in db.scalars(others.where(Receipt.image_hash == receipt.image_hash)):
        add(other, DuplicateReason.SAME_IMAGE)

    if receipt.image_phash:
        rows = db.execute(
            select(Receipt.id, Receipt.image_phash).where(
                Receipt.organization_id == receipt.organization_id,
                Receipt.id != receipt.id,
                Receipt.image_phash.is_not(None),
            )
        )
        close = [rid for rid, phash in rows if hamming_distance(phash, receipt.image_phash) <= SIMILAR_MAX_DISTANCE]
        if close:
            for other in db.scalars(select(Receipt).where(Receipt.id.in_(close))):
                add(other, DuplicateReason.SIMILAR_IMAGE)

    key = store_key(receipt.store_name)
    if key and receipt.paid_at is not None and receipt.total_amount is not None:
        # 날짜 비교는 DB마다 저장 형식이 달라서 금액으로 먼저 거르고 파이썬에서 분 단위 비교
        for other in db.scalars(others.where(Receipt.total_amount == receipt.total_amount)):
            if (
                other.paid_at is not None
                and _minute(other.paid_at) == _minute(receipt.paid_at)
                and store_key(other.store_name) == key
            ):
                add(other, DuplicateReason.SAME_DETAILS)

    ordered = sorted(found.values(), key=lambda m: (_STRENGTH[m.reason], -m.receipt.id))
    return ordered[:MAX_RESULTS]
