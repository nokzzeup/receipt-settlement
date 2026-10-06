"""공통 테스트 픽스처.

- 기본: 테스트 실행마다 임시 SQLite 파일을 새로 만들어 쓴다 → 개발 DB(backend/data/app.db)는 안 건드림
- TEST_DATABASE_URL을 지정하면 그 DB 사용 (예: PostgreSQL 호환 확인용. DB 이름은 _test로 끝나야 하고 미리 만들어둘 것)
- 테스트 하나가 끝나면 그 안에서 한 DB 변경은 전부 롤백 → 테스트끼리 서로 영향 없음
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, make_url
from sqlalchemy.orm import Session

import app.models  # noqa: F401  모든 모델을 Base.metadata에 등록
from app.core import ratelimit, security
from app.core.config import settings
from app.db.base import Base
from app.db.session import create_db_engine, get_db
from app.main import app
from app.ocr import MockOcrEngine, get_ocr_engine

# 테스트에선 고정 서명 키 사용 (backend/data/.jwt-secret 파일을 만들지 않게)
settings.jwt_secret = "test-only-secret-" + "x" * 40
security._secret.cache_clear()


@pytest.fixture(scope="session")
def engine(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Engine]:
    if settings.test_database_url:
        url = make_url(settings.test_database_url)
        # 실수로 개발 DB를 비우는 사고 방지
        if not (url.database or "").endswith("_test"):
            pytest.exit(f"TEST_DATABASE_URL의 DB 이름은 _test로 끝나야 합니다: {url.database}", returncode=1)
    else:
        url = make_url(f"sqlite:///{(tmp_path_factory.mktemp('db') / 'test.db').as_posix()}")

    engine = create_db_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    """테스트 끝나면 롤백되는 세션. 테스트 코드 안에서 commit() 해도 바깥 트랜잭션이 롤백한다."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def reset_login_limits() -> Iterator[None]:
    """로그인 실패 기록은 서버 메모리라 테스트끼리 섞이지 않게 매번 비움"""
    ratelimit.login_failures_by_account.reset()
    ratelimit.login_failures_by_ip.reset()
    yield


@pytest.fixture(autouse=True)
def storage_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """업로드 이미지는 테스트마다 임시 폴더에 저장 (backend/storage는 안 건드림)"""
    path = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", path)
    return path


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """API 테스트용 클라이언트. 앱의 get_db를 테스트 세션으로, OCR은 .env와 상관없이 Mock으로 바꿔 끼운다."""

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ocr_engine] = MockOcrEngine
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def signup(client: TestClient, email: str, name: str = "테스트", password: str = "password123") -> dict[str, str]:
    """가입하고 Authorization 헤더를 돌려준다"""
    response = client.post("/api/v1/auth/signup", json={"email": email, "password": password, "name": name})
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ---------- 조직·영수증 공통 헬퍼 ----------

ORGS = "/api/v1/orgs"
# 앞부분(매직 바이트)만 JPEG면 됨 — Mock OCR은 이미지 내용을 안 봄
FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def create_org(client: TestClient, headers: dict[str, str], name: str = "컴공 학생회") -> dict:
    response = client.post(ORGS, json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def join_org(client: TestClient, headers: dict[str, str], invite_code: str) -> dict:
    response = client.post(f"{ORGS}/join", json={"invite_code": invite_code}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def upload_receipt(
    client: TestClient, headers: dict[str, str], org_id: int, data: bytes = FAKE_JPEG, filename: str = "r.jpg"
):
    return client.post(
        f"{ORGS}/{org_id}/receipts", files={"image": (filename, data, "image/jpeg")}, headers=headers
    )
