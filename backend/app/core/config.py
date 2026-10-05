"""앱 설정. 우선순위: 실제 환경변수 > 레포 루트 .env > 아래 기본값.

레포 루트의 .env 하나를 백엔드와 프론트(Vite)가 같이 쓴다. 실행 위치와 무관하게 같은 파일을 읽는다.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_SQLITE_PATH = BACKEND_DIR / "data" / "app.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # .env 에 `KEY=` 처럼 비워두면 기본값 사용
        extra="ignore",  # VITE_* 등 백엔드가 안 쓰는 값은 무시
    )

    app_name: str = "영수증 정산 API"

    # DB. 기본은 SQLite 파일(backend/data/app.db) — 설치할 것 없음
    # PostgreSQL로 바꾸려면: pip install "psycopg[binary]" 후 postgresql+psycopg://user:pw@host:5432/db
    database_url: str = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
    # 비워두면 테스트마다 임시 SQLite 파일을 새로 만들어 사용 (tests/conftest.py)
    test_database_url: str | None = None

    # 로그인 토큰(JWT) 서명 키. 비워두면 backend/data/.jwt-secret 에 자동 생성해서 씀 (PC마다 다름, git 제외)
    jwt_secret: str | None = None
    # 로그인 유지 시간(분). 기본 7일 — 만료되면 다시 로그인
    jwt_expire_minutes: int = 60 * 24 * 7

    # OCR 엔진 전환: mock(고정 샘플) | paddle(3단계)
    ocr_engine: Literal["mock", "paddle"] = "mock"

    # 업로드 이미지 저장 폴더. 상대경로면 backend/ 기준
    storage_dir: Path = Path("storage")

    # 프론트를 다른 출처(origin)에서 띄울 때만 필요. 기본 개발 흐름은 Vite 프록시라 CORS 불필요
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    @property
    def storage_path(self) -> Path:
        return self.storage_dir if self.storage_dir.is_absolute() else BACKEND_DIR / self.storage_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
