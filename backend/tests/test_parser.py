"""파싱 1차(규칙 기반) 테스트. 3단계에서 실제 PaddleOCR 출력 샘플을 여기에 추가해 가며 규칙을 보강한다."""

from datetime import datetime

from app.core.timezone import KST
from app.ocr import MockOcrEngine, OcrLine, OcrRawResult
from app.parsing import ReceiptItem, parse
from app.parsing.rows import row_texts

H = 24  # 글자 높이


def raw_of(boxes: list[tuple[str, int, int, int]]) -> OcrRawResult:
    """(텍스트, x, y, 폭) 목록 → OCR 결과"""
    return OcrRawResult(
        engine="test",
        lines=[
            OcrLine(text=text, confidence=0.9, bbox=((x, y), (x + w, y), (x + w, y + H), (x, y + H)))
            for text, x, y, w in boxes
        ],
    )


def test_mock_sample() -> None:
    fields = parse(MockOcrEngine().recognize(b""))

    assert fields.store_name == "행복마트 테스트점"
    assert fields.paid_at == datetime(2026, 9, 28, 14, 32, 5, tzinfo=KST)
    assert fields.total_amount == 25400
    assert fields.items == [
        ReceiptItem(name="생수 2L", quantity=2, unit_price=1200, amount=2400),
        ReceiptItem(name="A4용지 500매", quantity=1, unit_price=6500, amount=6500),
        ReceiptItem(name="종이컵 50입", quantity=3, unit_price=1500, amount=4500),
        ReceiptItem(name="과자 세트", quantity=1, unit_price=12000, amount=12000),
    ]
    assert sum(item.amount for item in fields.items) == fields.total_amount


def test_header_columns_decide_quantity_and_unit_price() -> None:
    # 머리글 순서가 단가 → 수량 → 금액인 영수증
    fields = parse(
        raw_of(
            [
                ("카페 테스트", 200, 20, 150),
                ("2026/10/02 18:40", 60, 60, 220),
                ("메뉴", 60, 100, 60),
                ("단가", 300, 100, 60),
                ("수량", 400, 100, 60),
                ("금액", 500, 100, 60),
                ("아메리카노", 60, 140, 120),
                ("4,500", 290, 140, 70),
                ("3", 420, 141, 15),
                ("13,500", 490, 139, 75),
                ("합계", 60, 180, 60),
                ("13,500", 490, 180, 75),
            ]
        )
    )
    assert fields.items == [ReceiptItem(name="아메리카노", quantity=3, unit_price=4500, amount=13500)]
    assert fields.total_amount == 13500
    assert fields.paid_at == datetime(2026, 10, 2, 18, 40, tzinfo=KST)


def test_merged_boxes_without_header_and_discount() -> None:
    # 한 행이 통째로 박스 하나로 오고, 머리글이 없는 경우
    fields = parse(
        raw_of(
            [
                ("편의점 테스트점", 150, 20, 200),
                ("2026.10.01 09:05", 60, 60, 220),
                ("삼각김밥 1,200", 60, 100, 400),
                ("바나나우유 2 3,400", 60, 140, 400),
                ("행사할인 500", 60, 180, 400),
                ("합 계 4,100", 60, 220, 400),
                ("부가세 373", 60, 260, 400),
            ]
        )
    )
    assert fields.store_name == "편의점 테스트점"
    assert fields.paid_at == datetime(2026, 10, 1, 9, 5, tzinfo=KST)
    assert fields.total_amount == 4100
    assert fields.items == [
        ReceiptItem(name="삼각김밥", quantity=1, unit_price=None, amount=1200),
        ReceiptItem(name="바나나우유", quantity=2, unit_price=1700, amount=3400),
        ReceiptItem(name="행사할인", quantity=1, unit_price=None, amount=-500),  # 할인은 음수 품목
    ]
    assert sum(item.amount for item in fields.items) == fields.total_amount


def test_name_and_numbers_on_separate_rows() -> None:
    # 상품명 줄 아래에 바코드 + 숫자 줄이 찍히는 마트 영수증
    fields = parse(
        raw_of(
            [
                ("마트", 250, 20, 60),
                ("26-09-30 11:00", 60, 60, 200),
                ("상품명", 60, 100, 80),
                ("수량", 330, 100, 50),
                ("금액", 500, 100, 60),
                ("01 휴지 30롤", 60, 140, 160),
                ("*********4809", 60, 176, 160),
                ("1", 345, 176, 15),
                ("15,900", 490, 176, 70),
                ("합계", 60, 220, 60),
                ("15,900", 490, 220, 70),
            ]
        )
    )
    assert fields.items == [ReceiptItem(name="휴지 30롤", quantity=1, unit_price=None, amount=15900)]
    assert fields.paid_at == datetime(2026, 9, 30, 11, 0, tzinfo=KST)


def test_unreadable_receipt_gives_empty_fields() -> None:
    fields = parse(raw_of([("???", 10, 10, 30), ("흐릿함", 10, 60, 60)]))
    assert fields.paid_at is None
    assert fields.total_amount is None
    assert fields.items == []

    assert parse(OcrRawResult(engine="test", lines=[])).store_name is None


def test_row_texts_groups_boxes_by_line() -> None:
    texts = row_texts(MockOcrEngine().recognize(b""))
    assert texts[5] == "상품명 수량 단가 금액"
    assert texts[6] == "생수 2L 2 1,200 2,400"


def test_date_glued_to_time() -> None:
    # 실제 OCR에서 날짜와 시각 사이 공백이 빠지는 경우
    fields = parse(raw_of([("가게", 60, 20, 60), ("[판매] 2026.09.3018:42:17", 60, 60, 300)]))
    assert fields.paid_at == datetime(2026, 9, 30, 18, 42, 17, tzinfo=KST)


def test_tilted_photo_rows_are_still_grouped() -> None:
    # 사진을 5도 기울여 찍으면 오른쪽 금액 열이 한 줄 아래로 내려가 보인다 → 기울기를 되돌려서 같은 행으로 묶음
    import math

    angle = math.radians(5)
    original = MockOcrEngine().recognize(b"")
    tilted = OcrRawResult(
        engine="test",
        lines=[
            OcrLine(
                text=line.text,
                confidence=line.confidence,
                bbox=tuple(
                    (x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle) + 100)
                    for x, y in line.bbox
                ),
            )
            for line in original.lines
        ],
    )
    assert parse(tilted) == parse(original)


def test_paid_amount_beats_subtotal_and_receipt_discount_is_an_item() -> None:
    # '합계'는 할인 전, '결제금액'이 실제로 낸 돈
    fields = parse(
        raw_of(
            [
                ("가게", 60, 20, 60),
                ("상품명", 60, 60, 80),
                ("수량", 400, 60, 50),
                ("금액", 500, 60, 60),
                ("도시락", 60, 100, 80),
                ("1", 415, 100, 15),
                ("25,400", 490, 100, 75),
                ("합계", 60, 140, 60),
                ("25,400", 490, 140, 75),
                ("행사할인", 60, 180, 100),
                ("-1,000", 490, 180, 75),
                ("결제금액", 60, 220, 100),
                ("24,400", 490, 220, 75),
            ]
        )
    )
    assert fields.total_amount == 24400
    assert [(i.name, i.amount) for i in fields.items] == [("도시락", 25400), ("행사할인", -1000)]
    assert sum(i.amount for i in fields.items) == fields.total_amount


def test_store_name_from_label_line() -> None:
    fields = parse(
        raw_of(
            [
                ("*** 영수증 ***", 200, 20, 200),
                ("2026-10-08 12:00", 60, 60, 220),
                ("상호: 행복분식 정문점", 60, 100, 300),
                ("합계 8,000", 60, 140, 300),
            ]
        )
    )
    assert fields.store_name == "행복분식 정문점"
