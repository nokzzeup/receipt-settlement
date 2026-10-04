"""팀 규칙(시간 = timezone-aware, 금액 = int)을 DB 계층에서 강제하는 컬럼 타입.

SQLite는 PostgreSQL과 달리 시간대 정보를 저장하지 못하고(조용히 버림),
INTEGER 컬럼에 소수(1200.5)를 넣어도 그대로 저장해버린다. 아래 타입이 그 구멍을 막는다.
DDL(테이블 구조)은 기본 타입과 같고, 파이썬 쪽 변환·검사만 추가한다.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Dialect, Integer
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """timezone-aware datetime만 받는다. 저장 전에 UTC로 바꾸고, 읽을 때 UTC 시간대를 붙여서 돌려준다.

    - naive datetime(시간대 없음)을 넣으면 에러 → 영수증 시각은 KST를 붙여서 넣을 것 (app.core.timezone.KST)
    - 읽은 값은 항상 UTC 기준 aware datetime. 화면 표시는 Asia/Seoul로 변환
    """

    impl = DateTime(timezone=True)  # PostgreSQL: TIMESTAMPTZ / SQLite: DATETIME(UTC로 저장)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(f"시간대 없는 datetime은 저장할 수 없습니다: {value!r} (KST 또는 UTC를 붙여서 넣으세요)")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:  # SQLite: UTC로 저장해둔 값
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class StrictInteger(TypeDecorator[int]):
    """int만 받는 정수 컬럼 (금액·수량). float·Decimal·문자열·bool을 넣으면 에러."""

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"정수(int)만 저장할 수 있습니다: {value!r} ({type(value).__name__})")
        return value
