"""OCR 원문 → 영수증 필드 (1차 규칙 기반, 담당: 이성민).

2단계에서 확인·수정 화면 초기값을 채우려고 먼저 만든 버전이다. 3단계에서 실제 PaddleOCR 출력과
dataset/ 정답 라벨로 정확도를 재면서 규칙을 보강한다. 못 읽은 값은 None/빈 목록 → 사용자가 화면에서 채움.

처리 순서
1. 박스를 행으로 묶는다 (rows.py)
2. 가게명: '상호:·가맹점명:' 같은 표시가 있으면 그 값, 없으면 위쪽 몇 행 중 사업자·주소·날짜 같은 줄이 아닌 첫 행
3. 결제일시: 날짜 패턴이 있는 첫 행 (+ 같은 행의 시각). 한국시간(KST)으로 만든다
4. 합계: 실제 낸 돈을 가리키는 말부터 찾는다 — 결제금액·받을금액 > 합계·총액 > 카드결제·현금
   (할인이 있는 영수증은 '합계'가 할인 전 금액이고 '결제금액'이 실제 금액인 경우가 많음)
5. 품목: 표 머리글(상품명·수량·단가·금액) 다음 행부터 합계 행 전까지.
   머리글이 있으면 숫자를 머리글 열 위치로 수량/단가/금액에 배정하고, 없으면 숫자 개수로 추정한다.
"""

import re
from datetime import datetime

from app.core.timezone import KST
from app.ocr.schemas import OcrRawResult
from app.parsing.rows import Row, Token, group_rows
from app.parsing.schemas import ReceiptFields, ReceiptItem

_NUMBER = re.compile(r"-?\d{1,3}(?:,\d{3})+|-?\d+")
# 날짜. OCR이 날짜와 시각 사이 공백을 빼먹은 경우("2026.09.3018:42")도 일(日)을 두 자리로 끊어서 읽는다
_DATE = re.compile(
    r"(?<!\d)(20\d{2}|\d{2})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{2}(?=\d{1,2}\s*:\s*\d{2})|\d{1,2}(?!\d))"
)
_TIME = re.compile(r"(?<!\d)([01]?\d|2[0-3])\s*:\s*([0-5]\d)(?:\s*:\s*([0-5]\d))?(?!\d)")
_LEADING_INDEX = re.compile(r"^\d{1,3}[.)]?\s+")
_CODE_ONLY = re.compile(r"^[\d*\-\s]+$")

# 합계를 가리키는 말. 앞 묶음일수록 '실제로 낸 돈'에 가깝다 → 앞 묶음에서 먼저 찾는다
_TOTAL_TIERS: tuple[tuple[str, ...], ...] = (
    ("결제금액", "받을금액", "청구금액", "실결제", "결제합계"),
    ("합계", "총액", "총금액", "판매금액", "총구매액", "구매금액"),
    ("카드결제", "신용카드", "결제", "현금"),
)
_NOT_TOTAL = ("과세", "면세", "부가", "공급가", "할인", "봉사료", "거스름")
# 품목 구간 안에 있어도 품목이 아닌 줄. 할인 줄은 여기 넣지 않는다 → 음수 금액 품목으로 남겨서 품목 합계 = 합계가 되게
_NOT_ITEM = tuple(word for tier in _TOTAL_TIERS for word in tier) + (
    "과세", "면세", "부가", "공급가", "봉사료", "거스름", "받은금액", "잔액", "승인", "카드번호", "일시불", "할부",
    "가맹점", "사업자", "포인트", "적립", "회원", "멤버십", "현금영수증",
)
_DISCOUNT = ("할인", "에누리", "쿠폰")
_NOT_STORE = ("영수증", "매출전표", "고객용", "가맹점용", "재발행", "사업자", "대표", "TEL", "전화", "주소", "[")
_STORE_SEARCH_ROWS = 5
# "상호: 행복마트" / "가맹점명 행복마트" 처럼 가게 이름을 직접 표시한 줄
# (표시 뒤에 ':'나 공백이 있어야 함 → "상호저축은행" 같은 이름을 잘못 자르지 않게)
_STORE_LABEL = re.compile(
    r"^\s*(?:상\s*호\s*명?|가\s*맹\s*점\s*명|매\s*장\s*명|점\s*포\s*명|상\s*점\s*명)(?:\s*[:：]\s*|\s+)(?P<name>.+)$"
)

# 머리글 단어 → 열 이름
_HEADER_WORDS = {
    "상품명": "name",
    "품명": "name",
    "품목": "name",
    "메뉴": "name",
    "상품": "name",
    "수량": "quantity",
    "단가": "unit_price",
    "금액": "amount",
}


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def parse_int(token: str) -> int | None:
    """'1,200' / '1200원' / '-500' → int. 숫자만으로 된 토큰이 아니면 None"""
    text = token.strip().removesuffix("원").removeprefix("₩")
    if not _NUMBER.fullmatch(text):
        return None
    return int(text.replace(",", ""))


def _row_numbers(row: Row) -> list[int]:
    return [n for t in row.tokens() if (n := parse_int(t.text)) is not None]


# ---------- 결제일시 ----------


def _find_paid_at(rows: list[Row]) -> datetime | None:
    for row in rows:
        text = row.text
        for match in _DATE.finditer(text):
            year, month, day = (int(g) for g in match.groups())
            if year < 100:
                year += 2000
            time_match = _TIME.search(text[match.end() :])  # 잘라서 찾아야 붙어 있는 시각도 잡힘
            hour, minute, second = (0, 0, 0)
            if time_match:
                hour, minute = int(time_match.group(1)), int(time_match.group(2))
                second = int(time_match.group(3) or 0)
            try:
                return datetime(year, month, day, hour, minute, second, tzinfo=KST)
            except ValueError:
                continue  # 13월 같은 값 → 날짜가 아님
    return None


# ---------- 합계 ----------


def _label(row: Row) -> str:
    """행에서 숫자 토큰을 뺀 글자 (공백 제거)"""
    return _compact("".join(t.text for t in row.tokens() if parse_int(t.text) is None))


def _is_total_row(row: Row, keywords: tuple[str, ...]) -> bool:
    label = _label(row)
    return any(k in label for k in keywords) and not any(k in label for k in _NOT_TOTAL)


def _find_total(rows: list[Row]) -> tuple[int | None, int | None]:
    """(합계 금액, 합계 행 번호)"""
    for keywords in _TOTAL_TIERS:
        for index, row in enumerate(rows):
            if _is_total_row(row, keywords):
                numbers = _row_numbers(row)
                if numbers and numbers[-1] >= 0:
                    return numbers[-1], index
    return None, None


# ---------- 가게명 ----------


def _find_store_name(rows: list[Row]) -> str | None:
    for row in rows:
        if (match := _STORE_LABEL.match(row.text)) and sum(ch.isalpha() for ch in match["name"]) >= 2:
            return match["name"].strip()[:100]
    for row in rows[:_STORE_SEARCH_ROWS]:
        text = row.text.strip()
        if any(word in text for word in _NOT_STORE) or _DATE.search(text):
            continue
        letters = sum(ch.isalpha() for ch in text)
        if letters < 2:
            continue
        return text[:100]
    return None


# ---------- 품목 ----------


def _header_columns(row: Row) -> dict[str, float] | None:
    """머리글 행이면 {열 이름: x 중심}. 수량/단가/금액 중 하나 + 상품명이 있어야 머리글로 본다"""
    columns: dict[str, float] = {}
    for token in row.tokens():
        column = _HEADER_WORDS.get(_compact(token.text))
        if column and column not in columns:
            columns[column] = token.center_x
    if "name" in columns and len(columns) >= 2:
        return columns
    return None


def _assign_by_header(tokens: list[Token], columns: dict[str, float]) -> tuple[list[str], dict[str, int]]:
    """토큰마다 가장 가까운 머리글 열에 배정. 상품명 열 쪽 토큰은 이름으로"""
    name_parts: list[str] = []
    values: dict[str, int] = {}
    for token in tokens:
        number = parse_int(token.text)
        column = min(columns, key=lambda c: abs(columns[c] - token.center_x))
        if number is None or column == "name" or column in values:
            name_parts.append(token.text)
        else:
            values[column] = number
    return name_parts, values


def _assign_by_count(tokens: list[Token]) -> tuple[list[str], dict[str, int]]:
    """머리글이 없을 때: 오른쪽 끝의 숫자(최대 3개)를 금액 쪽 값으로 보고 개수·곱셈 관계로 추정"""
    numbers: list[int] = []
    split = len(tokens)
    while split > 0 and len(numbers) < 3 and (n := parse_int(tokens[split - 1].text)) is not None:
        numbers.insert(0, n)
        split -= 1
    name_parts = [t.text for t in tokens[:split]]
    if not numbers:
        return name_parts, {}
    amount = numbers[-1]
    values = {"amount": amount}
    if len(numbers) == 3:
        a, b = numbers[0], numbers[1]
        if a * b == amount:
            values["quantity"], values["unit_price"] = min(a, b), max(a, b)
    elif len(numbers) == 2:
        a = numbers[0]
        if a == amount:
            values["unit_price"] = a
        elif 0 < a <= 99 and amount % a == 0:
            values["quantity"], values["unit_price"] = a, amount // a
        elif a > 0 and amount % a == 0:
            values["unit_price"], values["quantity"] = a, amount // a
    return name_parts, values


def _clean_name(parts: list[str]) -> str:
    name = _LEADING_INDEX.sub("", " ".join(parts)).strip()
    return "" if _CODE_ONLY.fullmatch(name or "0") else name


def _make_item(name: str, values: dict[str, int]) -> ReceiptItem | None:
    amount = values.get("amount")
    if amount is None:
        return None
    quantity = values.get("quantity", 1)
    unit_price = values.get("unit_price")
    if quantity <= 0:
        quantity = 1
    if any(word in name for word in _DISCOUNT):
        return ReceiptItem(name=name, quantity=1, unit_price=None, amount=-abs(amount))
    return ReceiptItem(name=name, quantity=quantity, unit_price=unit_price, amount=amount)


def _find_items(rows: list[Row], total_index: int | None) -> list[ReceiptItem]:
    end = total_index if total_index is not None else len(rows)
    header_index, columns = None, None
    for index, row in enumerate(rows[:end]):
        if (found := _header_columns(row)) is not None:
            header_index, columns = index, found
            break

    if header_index is not None:
        start = header_index + 1
    else:
        # 머리글이 없으면 날짜 행 다음부터 (가게 정보·주소 줄을 품목으로 오인하지 않게)
        start = next((i + 1 for i, row in enumerate(rows[:end]) if _DATE.search(row.text)), 0)

    items: list[ReceiptItem] = []
    pending_name = ""  # 이름만 있고 숫자는 다음 행에 찍히는 영수증 대비
    for row in rows[start:end]:
        if any(word in _label(row) for word in _NOT_ITEM):
            pending_name = ""
            continue
        tokens = row.tokens()
        name_parts, values = _assign_by_header(tokens, columns) if columns else _assign_by_count(tokens)
        name = _clean_name(name_parts)
        if "amount" not in values:
            pending_name = name
            continue
        if not name:
            name = pending_name
        pending_name = ""
        if not name:
            continue
        if columns is None and abs(values["amount"]) < 100 and "," not in row.text:
            continue  # 머리글 없이 작은 숫자 하나뿐인 줄(주소 번지 등)은 품목으로 안 봄
        if (item := _make_item(name[:200], values)) is not None:
            items.append(item)
    return items


def parse(raw: OcrRawResult) -> ReceiptFields:
    """OCR 원문 → 영수증 필드. 읽지 못한 값은 None / 빈 목록.

    MockOcrEngine 샘플로 바로 확인: parse(MockOcrEngine().recognize(b""))
    """
    rows = group_rows(raw)
    total, total_index = _find_total(rows)
    return ReceiptFields(
        store_name=_find_store_name(rows),
        paid_at=_find_paid_at(rows),
        total_amount=total,
        items=_find_items(rows, total_index),
    )
