"""비밀번호 해시 + 로그인 토큰(JWT).

- 비밀번호는 argon2 해시로만 저장 (원문 저장 금지)
- 토큰에는 사용자 id만 넣는다. 조직·역할은 토큰에 넣지 않고 요청마다 DB의 멤버십으로 확인
  (역할이 바뀌거나 조직에서 빠지면 바로 반영되게)
"""

import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

_password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


@lru_cache
def _dummy_hash() -> str:
    return _password_hash.hash(secrets.token_urlsafe(16))


def verify_password_for_missing_user(password: str) -> None:
    """없는 이메일로 로그인할 때도 해시 검증 시간만큼 걸리게 해서, 응답 시간으로 가입 여부를 알아내지 못하게 함"""
    _password_hash.verify(password, _dummy_hash())


@lru_cache
def _secret() -> str:
    if settings.jwt_secret:
        return settings.jwt_secret
    path = settings.data_path / ".jwt-secret"  # 개발: backend/data, 서버 모드: server-data
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def create_access_token(user_id: int) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=settings.jwt_expire_minutes)}
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """유효하면 user_id, 아니면(만료·위조·형식 오류) None"""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
