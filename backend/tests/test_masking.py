import pytest

from app.ocr import MockOcrEngine
from app.receipts.masking import mask_card_numbers, mask_ocr_result


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("카드번호 9410-12**-****-3456", "카드번호 ****-****-****-3456"),
        ("1234 5678 9012 3456", "**** **** **** 3456"),
        ("9410123456783456", "************3456"),
        ("3712-345678-12345", "****-******-*2345"),  # 아멕스 4-6-5
        ("536510******1234", "************1234"),
        ("****-****-****-****", "****-****-****-****"),
    ],
)
def test_card_numbers_are_masked(text: str, expected: str) -> None:
    assert mask_card_numbers(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "승인번호 30012345",  # 8자리: 중복 영수증 감지에 쓸 수 있게 남김
        "사업자번호 123-45-67890",
        "TEL 02-123-4567",
        "010-1234-5678",
        "합계 1,234,567",
        "[판매] 2026-09-28 14:32:05",
    ],
)
def test_other_numbers_are_kept(text: str) -> None:
    assert mask_card_numbers(text) == text


def test_mask_ocr_result_keeps_original_untouched() -> None:
    raw = MockOcrEngine().recognize(b"")
    masked = mask_ocr_result(raw)

    assert any("9410" in line.text for line in raw.lines)
    assert not any("9410" in line.text for line in masked.lines)
    assert [line.bbox for line in masked.lines] == [line.bbox for line in raw.lines]
    assert masked.engine == raw.engine
