"""모델 공통 요소."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


def str_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """StrEnum → VARCHAR(20) + CHECK 제약. name은 CHECK 제약 이름에 쓰인다."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        validate_strings=True,
    )
