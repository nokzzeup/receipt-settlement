"""SQLAlchemy 선언 기반(Base).

- 제약조건 이름 규칙(naming_convention): Alembic이 제약조건을 이름으로 찾아 수정/삭제할 수 있게 함
  (SQLite에서 테이블을 고칠 때 쓰는 batch 모드는 이름 없는 제약조건을 다루지 못함)
- datetime 컬럼은 기본으로 UTCDateTime (timezone-aware 강제, app/db/types.py)
"""

from datetime import datetime

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from app.db.types import UTCDateTime

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {datetime: UTCDateTime()}
