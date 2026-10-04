"""DB 계층이 팀 규칙(시간대·정수 금액·외래키)을 실제로 지키는지 확인.

SQLite는 기본 상태로는 셋 다 안 지킨다 → app/db/types.py, app/db/sqlite.py 보정이 깨지면 여기서 잡힌다.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.core.timezone import KST
from app.models import Category, Membership, Organization, Receipt, User


def _org(db: Session) -> tuple[Organization, Membership]:
    user = User(email="treasurer@example.com", password_hash="x", name="총무")
    org = Organization(name="테스트 동아리", invite_code="TEST0001", created_by=user)
    membership = Membership(organization=org, user=user)
    db.add_all([user, org, membership])
    db.flush()
    return org, membership


def test_datetime_keeps_the_same_instant(db_session: Session) -> None:
    org, membership = _org(db_session)
    paid_at = datetime(2026, 9, 28, 14, 32, tzinfo=KST)
    db_session.add(
        Receipt(organization_id=org.id, uploader=membership, image_path="a.jpg", image_hash="0" * 64, paid_at=paid_at)
    )
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.scalar(select(Receipt.paid_at))
    assert loaded is not None and loaded.tzinfo is not None
    assert loaded == paid_at  # 같은 시각 (14:32 KST == 05:32 UTC)
    assert loaded.astimezone(KST).hour == 14


def test_naive_datetime_is_rejected(db_session: Session) -> None:
    org, membership = _org(db_session)
    db_session.add(
        Receipt(
            organization_id=org.id,
            uploader=membership,
            image_path="a.jpg",
            image_hash="0" * 64,
            paid_at=datetime(2026, 9, 28, 14, 32),  # 시간대 없음
        )
    )
    with pytest.raises(StatementError, match="시간대"):
        db_session.flush()


def test_server_default_timestamps_are_utc(db_session: Session) -> None:
    org, _ = _org(db_session)
    db_session.commit()
    db_session.expire_all()

    created_at = db_session.get(Organization, org.id).created_at  # type: ignore[union-attr]
    assert created_at.tzinfo is not None
    assert abs((datetime.now(UTC) - created_at).total_seconds()) < 60


def test_float_amount_is_rejected(db_session: Session) -> None:
    org, _ = _org(db_session)
    db_session.add(Category(organization=org, name="비품", budget_amount=1000.5))  # type: ignore[arg-type]
    with pytest.raises(StatementError, match="정수"):
        db_session.flush()


def test_foreign_keys_are_enforced(db_session: Session) -> None:
    db_session.add(Category(organization_id=999_999, name="없는 조직"))
    with pytest.raises(IntegrityError):
        db_session.flush()
