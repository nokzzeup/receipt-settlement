"""DB 엔진·세션. 동기(sync) SQLAlchemy 사용 → DB를 쓰는 라우터는 `async def`가 아니라 `def`로 작성."""

from collections.abc import Iterator

from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.sqlite import SQLITE_CONNECT_ARGS, apply_sqlite_fixes, ensure_sqlite_dir, is_sqlite


def create_db_engine(url: str | URL) -> Engine:
    """앱·테스트 공용 엔진. 기본은 SQLite, DATABASE_URL을 바꾸면 PostgreSQL도 그대로 동작."""
    if is_sqlite(url):
        ensure_sqlite_dir(url)
        engine = create_engine(url, connect_args=SQLITE_CONNECT_ARGS)
        apply_sqlite_fixes(engine)
        return engine
    return create_engine(url, pool_pre_ping=True)


engine = create_db_engine(settings.database_url)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI 의존성: 요청 하나당 세션 하나. commit은 라우터/서비스에서 명시적으로 호출한다."""
    with SessionLocal() as session:
        yield session
