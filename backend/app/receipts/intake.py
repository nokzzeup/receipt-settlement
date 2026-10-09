"""영수증 접수: 이미지 저장 → OCR → 카드번호 마스킹 → 파싱 → 품목 자동 분류 → 작성 중(DRAFT) 지출 생성.

OCR·파싱이 실패해도 업로드 자체는 성공시킨다 (빈 값으로 만들고 사용자가 직접 입력).
마스킹을 못 거친 OCR 결과는 절대 저장하지 않는다.
"""

import hashlib
import logging
import threading
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.classify import classify_names
from app.models import CategorySource, Expense, ExpenseItem, ExpenseStatus, Membership, Receipt
from app.ocr import OcrEngine, OcrRawResult
from app.parsing import ReceiptFields, ReceiptItem, parse
from app.receipts.images import ImageType
from app.receipts.masking import mask_ocr_result
from app.receipts.storage import delete_image, save_receipt_image
from app.schemas.common import MAX_AMOUNT, MAX_ITEMS, MAX_QUANTITY

logger = logging.getLogger(__name__)

# OCR은 한 번에 한 장씩. PaddleOCR 같은 엔진은 CPU·메모리를 많이 쓰고 동시 호출을 보장하지 않아서,
# 여러 명이 동시에 올리면 뒤 사람은 앞 사람 인식이 끝날 때까지 기다린다 (동아리 규모면 몇 초)
_ocr_lock = threading.Lock()


@dataclass(frozen=True)
class Recognized:
    raw: OcrRawResult | None  # None = OCR 실패
    fields: ReceiptFields


def recognize(engine: OcrEngine, image_bytes: bytes) -> Recognized:
    try:
        with _ocr_lock:
            result = engine.recognize(image_bytes)
        raw = mask_ocr_result(result)
    except Exception:
        logger.exception("OCR 실패 (engine=%s)", getattr(engine, "name", "?"))
        return Recognized(raw=None, fields=ReceiptFields())
    try:
        fields = parse(raw)
    except Exception:
        logger.exception("영수증 파싱 실패")
        fields = ReceiptFields()
    return Recognized(raw=raw, fields=fields)


def _in_range(value: int | None, low: int, high: int) -> int | None:
    return value if value is not None and low <= value <= high else None


def _sanitize_item(item: ReceiptItem) -> ReceiptItem | None:
    """DB 제약·API 입력 규칙에 맞게 다듬는다. 금액을 못 쓰면 품목에서 뺀다 (OCR 오인식 대비)"""
    amount = _in_range(item.amount, -MAX_AMOUNT, MAX_AMOUNT)
    name = item.name.strip()[:200]
    if amount is None or not name:
        return None
    return ReceiptItem(
        name=name,
        quantity=_in_range(item.quantity, 1, MAX_QUANTITY) or 1,
        unit_price=_in_range(item.unit_price, -MAX_AMOUNT, MAX_AMOUNT),
        amount=amount,
    )


def sanitize(fields: ReceiptFields) -> ReceiptFields:
    items = [clean for item in fields.items if (clean := _sanitize_item(item)) is not None]
    store_name = (fields.store_name or "").strip()[:200] or None
    return ReceiptFields(
        store_name=store_name,
        paid_at=fields.paid_at,
        total_amount=_in_range(fields.total_amount, 0, MAX_AMOUNT),
        items=items[:MAX_ITEMS],
    )


def create_draft_expense(
    db: Session, uploader: Membership, image_bytes: bytes, image_type: ImageType, engine: OcrEngine
) -> Expense:
    """영수증 1장 → 작성 중 지출 1건. 결제자 기본값은 올린 사람"""
    relative_path = save_receipt_image(uploader.organization_id, image_bytes, image_type.extension)
    try:
        recognized = recognize(engine, image_bytes)
        fields = sanitize(recognized.fields)
        receipt = Receipt(
            organization_id=uploader.organization_id,
            uploader_membership_id=uploader.id,
            image_path=relative_path,
            image_hash=hashlib.sha256(image_bytes).hexdigest(),
            ocr_raw=recognized.raw.model_dump(mode="json") if recognized.raw else None,
            store_name=fields.store_name,
            paid_at=fields.paid_at,
            total_amount=fields.total_amount,
        )
        # 품목 → 계정과목 자동 분류. 못 고른 품목은 미분류(None) → 확인 화면에서 사용자가 고름
        category_ids = classify_names(db, uploader.organization_id, [i.name for i in fields.items])
        expense = Expense(
            organization_id=uploader.organization_id,
            receipt=receipt,
            payer_membership_id=uploader.id,
            status=ExpenseStatus.DRAFT,
            items=[
                ExpenseItem(
                    name=i.name,
                    quantity=i.quantity,
                    unit_price=i.unit_price,
                    amount=i.amount,
                    category_id=category_id,
                    category_source=CategorySource.AUTO if category_id is not None else None,
                )
                for i, category_id in zip(fields.items, category_ids, strict=True)
            ],
        )
        db.add_all([receipt, expense])
        db.commit()
    except BaseException:
        db.rollback()
        delete_image(relative_path)
        raise
    return expense
