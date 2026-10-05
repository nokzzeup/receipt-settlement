"""여러 스키마에서 같이 쓰는 값 타입.

금액은 원 단위 int만 (StrictInt: 1200.0 같은 float, "1200" 같은 문자열은 422).
상한은 DB INTEGER 범위(PostgreSQL 기준 약 21억)보다 충분히 낮게 잡아서 합계를 내도 넘치지 않게 한다.
"""

from typing import Annotated

from pydantic import BeforeValidator, Field, StrictInt, StringConstraints

MAX_AMOUNT = 1_000_000_000  # 10억 원
MAX_QUANTITY = 10_000
MAX_ITEMS = 100  # 지출 1건의 품목 수

# 금액(원). 할인 줄은 음수일 수 있음
Won = Annotated[StrictInt, Field(ge=-MAX_AMOUNT, le=MAX_AMOUNT)]
# 0 이상 금액(원): 예산, 영수증 합계
NonNegativeWon = Annotated[StrictInt, Field(ge=0, le=MAX_AMOUNT)]
Quantity = Annotated[StrictInt, Field(ge=1, le=MAX_QUANTITY)]


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


# 앞뒤 공백 제거. 빈 문자열은 None으로 (선택 입력란)
OptionalText200 = Annotated[
    Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None,
    BeforeValidator(_blank_to_none),
]
Text200 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
