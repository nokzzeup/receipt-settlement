"""시간 규칙: DB에는 timezone-aware(TIMESTAMPTZ)로 저장, 화면 표시는 Asia/Seoul.

영수증에 찍힌 시각은 한국시간이므로, 파싱할 때 naive datetime에 KST를 붙여서 만든다.
    datetime(2026, 9, 28, 14, 32, tzinfo=KST)
"""

from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime:
    return datetime.now(KST)
