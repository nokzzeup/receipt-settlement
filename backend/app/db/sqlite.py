"""SQLite 보정. 앱·테스트 엔진에만 적용한다 (마이그레이션 엔진은 제외 → migrations/env.py 참고)

1. 외래키 검사 켜기 — SQLite는 기본으로 꺼져 있어서, 안 켜면 없는 조직 ID도 그냥 저장되고
   ON DELETE CASCADE도 동작하지 않는다
2. WAL 모드 — 읽기와 쓰기가 서로 막지 않음 (여러 폰에서 동시에 쓸 때 "database is locked" 감소)
3. 트랜잭션 시작(BEGIN)을 SQLAlchemy가 직접 관리 — 파이썬 sqlite3 드라이버의 옛날 방식(SELECT는 트랜잭션
   밖에서 실행, SAVEPOINT 오동작)을 끈다. SQLAlchemy 공식 문서의 권장 방식 그대로
   https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#sqlite-transactions
"""

import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import URL, Engine, event, make_url

# Python 3.16부터 sqlite3 기본 동작이 바뀌어도 아래 보정이 그대로 동작하게 옛 방식을 명시적으로 고정
SQLITE_CONNECT_ARGS: dict[str, Any] = {"autocommit": sqlite3.LEGACY_TRANSACTION_CONTROL}


def is_sqlite(url: str | URL) -> bool:
    return make_url(url).get_backend_name() == "sqlite"


def ensure_sqlite_dir(url: str | URL) -> None:
    """DB 파일이 들어갈 폴더가 없으면 만든다 (SQLite는 파일은 만들어도 폴더는 안 만듦)."""
    database = make_url(url).database
    if database and database != ":memory:":
        Path(database).parent.mkdir(parents=True, exist_ok=True)


def apply_sqlite_fixes(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection: sqlite3.Connection, _: Any) -> None:
        dbapi_connection.isolation_level = None  # 드라이버가 BEGIN을 내지 않게 함 → 아래 _on_begin이 담당
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.close()

    @event.listens_for(engine, "begin")
    def _on_begin(connection: Any) -> None:
        connection.exec_driver_sql("BEGIN")
