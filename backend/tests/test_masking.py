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


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # 실제 PaddleOCR 출력: 하이픈 하나를 _ 로 읽음
        ("카드번호 5365-10**_****-7788", "카드번호 ****-****_****-7788"),
        # 가린 자리를 x·# 로 읽은 경우
        ("5365-10xx-xxxx-7788", "****-**xx-xxxx-7788"),
        # 형식이 깨져서(0을 O로 읽음) 패턴에 안 걸려도 '카드번호' 뒤 숫자는 마지막 4자리만 남김
        ("카드번호: 5365 1O** **** 7788", "카드번호: **** *O** **** 7788"),
        ("CARD NO 4518 4212 3456 7788", "CARD NO **** **** **** 7788"),
    ],
)
def test_ocr_mistakes_in_card_numbers_are_still_masked(text: str, expected: str) -> None:
    assert mask_card_numbers(text) == expected


@pytest.mark.parametrize("text", ["[판매] 2026.09.30 18:42:17", "신용카드 18,600", "카드번호 ****-****-****-3456"])
def test_keyword_masking_leaves_other_lines_alone(text: str) -> None:
    assert mask_card_numbers(text) == text
