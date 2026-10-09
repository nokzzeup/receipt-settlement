"""품목명·계정과목 이름 정규화 — 규칙 저장과 비교를 같은 기준으로 하기 위해.

    "제주 삼다수 2L"      → "제주삼다수"
    "제주삼다수 500ml"    → "제주삼다수"   (용량·개수가 달라도 같은 품목으로 본다)
    "[1+1] 포카칩(대)"    → "포카칩"
    "A4용지 500매"        → "a용지"        (숫자는 전부 빠지므로 키워드도 같은 함수로 정규화해서 비교)
"""

import re
import unicodedata

# 괄호 안 내용: (대), [1+1], <행사> 같은 꾸밈말. 전각 괄호는 NFKC가 반각으로 바꿔줌
_BRACKETED = re.compile(r"[(\[{<【][^)\]}>】]*[)\]}>】]")
# 숫자 + 단위: 2L, 500ml, 50입, 3개, 1.5kg, 2x ...
_NUMBER_WITH_UNIT = re.compile(
    r"\d+(?:[.,]\d+)*\s*(?:ml|mm|cm|kg|mg|g|l|m|개입|개|입|매|팩|병|캔|봉|ea|p|x|구|장|권|세트|set)?"
)
_NOT_WORD = re.compile(r"[^a-z가-힣]")


def normalize_name(name: str) -> str:
    """소문자 + 한글·영문만 남김. 괄호 속 꾸밈말을 빼면 아무것도 안 남으면 괄호 속을 살린다"""
    text = unicodedata.normalize("NFKC", name).lower()
    without_brackets = _BRACKETED.sub(" ", text)
    if _strip(without_brackets):
        text = without_brackets
    return _strip(text)


def _strip(text: str) -> str:
    return _NOT_WORD.sub("", _NUMBER_WITH_UNIT.sub("", text))
