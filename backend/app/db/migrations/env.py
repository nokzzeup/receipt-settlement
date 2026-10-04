"""Alembic 실행 환경.

- 접속 주소: alembic.ini가 아니라 앱 설정(DATABASE_URL, 기본 SQLite)을 그대로 사용
- autogenerate 대상: app.models 에 등록된 모든 모델 (Base.metadata)
- render_as_batch: SQLite는 컬럼·제약조건 수정(ALTER)을 거의 지원하지 않아서, Alembic이 테이블을
  새로 만들어 데이터를 옮기는 방식(batch)으로 마이그레이션을 생성한다. PostgreSQL에서도 그대로 동작
- 마이그레이션 엔진은 일부러 외래키 검사를 켜지 않는다 (app/db/sqlite.py의 보정 미적용).
  batch 방식은 테이블을 지웠다 다시 만드는데, 외래키 검사가 켜져 있으면 그 순간
  ON DELETE CASCADE가 동작해서 자식 데이터(지출 품목 등)가 같이 지워진다
"""

from logging.config import fileConfig
from typing import Any

from alembic import context
from alembic.autogenerate.api import AutogenContext
from sqlalchemy import create_engine, pool
from sqlalchemy.types import TypeDecorator

import app.models  # noqa: F401  모든 모델을 Base.metadata에 등록
from app.core.config import settings
from app.db.base import Base
from app.db.sqlite import ensure_sqlite_dir

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    # 스크립트/테스트에서 config.set_main_option("sqlalchemy.url", ...)로 덮어쓸 수 있게 해둠
    return config.get_main_option("sqlalchemy.url") or settings.database_url


def render_item(type_: str, obj: Any, autogen_context: AutogenContext) -> str | bool:
    """커스텀 타입(UTCDateTime, StrictInteger)은 파이썬 쪽 변환만 하므로 마이그레이션 파일에는
    기본 SQL 타입(sa.DateTime 등)으로 기록 → 마이그레이션이 앱 코드 변경에 영향받지 않게 함"""
    if type_ == "type" and isinstance(obj, TypeDecorator):
        return f"sa.{obj.impl!r}"
    return False


def _configure_options() -> dict[str, Any]:
    return {"target_metadata": target_metadata, "render_as_batch": True, "render_item": render_item}


def run_migrations_offline() -> None:
    """DB 접속 없이 SQL만 출력 (alembic upgrade head --sql)."""
    context.configure(
        url=_database_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_configure_options(),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _database_url()
    ensure_sqlite_dir(url)
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, **_configure_options())
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
