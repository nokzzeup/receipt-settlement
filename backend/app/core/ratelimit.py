"""로그인 실패 횟수 제한 (서버 메모리).

공용 서버를 인터넷(터널)에 열면 누구나 로그인 화면까지 올 수 있다. 비밀번호를 계속 바꿔 넣는 공격을
늦추는 최소한의 장치:
- 같은 IP + 같은 이메일로 10분 안에 10번 틀리면 → 잠시 차단 (429)
- 같은 IP에서 이메일을 바꿔 가며 10분 안에 30번 틀려도 → 차단
- 로그인에 성공하면 그 IP + 이메일의 실패 기록은 지운다
- 서버를 다시 켜면 초기화 (워커 1개 구조라 메모리로 충분)

터널을 거쳐 온 요청의 IP는 uvicorn이 X-Forwarded-For로 실제 접속자 IP로 바꿔준다 (127.0.0.1에서 온 프록시만 신뢰).
"""

import math
import threading
import time
from collections import deque


class FailureLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> deque[float]:
        times = self._failures.get(key)
        if times is None:
            return deque()
        while times and times[0] <= now - self.window:
            times.popleft()
        if not times:
            del self._failures[key]
        return times

    def retry_after(self, key: str, now: float | None = None) -> int:
        """막혀 있으면 다시 시도할 수 있을 때까지 남은 초, 아니면 0"""
        now = time.monotonic() if now is None else now
        with self._lock:
            times = self._recent(key, now)
            if len(times) < self.limit:
                return 0
            return max(1, math.ceil(times[0] + self.window - now))

    def record(self, key: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            self._recent(key, now)
            self._failures.setdefault(key, deque()).append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_failures_by_account = FailureLimiter(limit=10, window_seconds=600)
login_failures_by_ip = FailureLimiter(limit=30, window_seconds=600)
