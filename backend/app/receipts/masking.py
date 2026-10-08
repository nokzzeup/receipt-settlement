"""OCR 원문의 카드번호 마스킹 — 저장(DB)·파싱 전에 반드시 거친다.

카드번호로 보는 형태 (숫자 자리에 이미 * 가 섞여 있어도 같은 취급)
- 4-4-4-4 처럼 4자리씩 구분: 9410-12**-****-3456, 1234 5678 9012 3456
  OCR이 하이픈을 _ . ~ = 등으로 잘못 읽은 것(5365-10**_****-7788 — 실제로 나옴)도 포함
- 아멕스 4-6-5: 3712-345678-12345
- 구분자 없이 13~19자리 연속: 9410123456783456
- "카드번호" 글자가 있는 줄은 형식이 깨져서 위에 안 걸려도 그 뒤 숫자를 마지막 4자리만 남기고 가린다

마스킹하면 마지막 4자리만 남는다: 9410-12**-****-3456 → ****-****-****-3456

일부러 넓게 잡는다 (개인정보 쪽으로 틀리는 게 낫다)
- 13자리 이상 연속 숫자(바코드·거래번호 등)도 가려질 수 있음 → 파싱에는 필요 없는 값이라 괜찮음
- 전화번호(10~11자리)·사업자번호(10자리)·승인번호(8자리)·금액(쉼표 구분)은 해당 안 됨
"""

import re

from app.ocr.schemas import OcrLine, OcrRawResult

_D = r"[\d*xX#]"  # 숫자 또는 이미 가려진 자리 (OCR이 *를 x·#로 읽기도 함)
_S = r"(?:\s?[-_.~=–−—]\s?|\s)"  # 구분자 (OCR이 하이픈을 다른 기호로 읽는 경우 포함)
_CARD_PATTERN = re.compile(
    rf"(?<![\d*xX#])(?:"
    rf"{_D}{{4}}(?:{_S}{_D}{{4}}){{2}}{_S}{_D}{{1,7}}"  # 4-4-4-(1~7)
    rf"|{_D}{{4}}{_S}{_D}{{6}}{_S}{_D}{{4,5}}"  # 4-6-5 (아멕스), 4-6-4 (다이너스)
    rf"|{_D}{{13,19}}"  # 구분자 없음
    rf")(?![\d*xX#])"
)
_CARD_KEYWORD = re.compile(r"카드\s*번호|카드\s*no\.?|card\s*no\.?", re.IGNORECASE)


def _mask_match(match: re.Match[str]) -> str:
    return _keep_last_digits(match.group())


def _keep_last_digits(text: str, keep: int = 4) -> str:
    keep_from = len(text)
    kept = 0
    # 뒤에서부터 숫자 4개까지는 남긴다
    for index in range(len(text) - 1, -1, -1):
        if text[index].isdigit():
            kept += 1
            if kept > keep:
                break
            keep_from = index
    return "".join("*" if ch.isdigit() and i < keep_from else ch for i, ch in enumerate(text))


def mask_card_numbers(text: str) -> str:
    text = _CARD_PATTERN.sub(_mask_match, text)
    keyword = _CARD_KEYWORD.search(text)
    if keyword:  # 형식이 깨져서 패턴에 안 걸린 카드번호도: 키워드 뒤 숫자는 마지막 4자리만 남김
        head, tail = text[: keyword.end()], text[keyword.end() :]
        if sum(ch.isdigit() for ch in tail) > 4:
            text = head + _keep_last_digits(tail)
    return text


def mask_ocr_result(raw: OcrRawResult) -> OcrRawResult:
    """원본은 그대로 두고 마스킹한 사본을 돌려준다"""
    return OcrRawResult(
        engine=raw.engine,
        lines=[
            OcrLine(text=mask_card_numbers(line.text), confidence=line.confidence, bbox=line.bbox)
            for line in raw.lines
        ],
    )
