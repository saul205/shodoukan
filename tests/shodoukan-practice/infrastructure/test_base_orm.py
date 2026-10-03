"""UtcDateTime: naive UTC in the database, aware UTC in the backend."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from factories import USER_ID
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from shodoukan_practice.infrastructure.db.orm import UserORM

MADRID_SUMMER = timezone(timedelta(hours=2))


def test_stores_naive_utc(session: Session) -> None:
    moment = datetime(2026, 7, 1, 12, 0, tzinfo=MADRID_SUMMER)
    session.add(
        UserORM(id=USER_ID, username="kana", created_at=moment, updated_at=moment)
    )
    session.flush()

    raw = session.execute(
        text("SELECT created_at FROM users WHERE username = 'kana'")
    ).scalar_one()
    assert str(raw).startswith("2026-07-01 10:00:00")


def test_returns_aware_utc(session: Session) -> None:
    moment = datetime(2026, 7, 1, 12, 0, tzinfo=MADRID_SUMMER)
    session.add(
        UserORM(id=USER_ID, username="kana", created_at=moment, updated_at=moment)
    )
    session.commit()
    session.expunge_all()

    stored = session.scalars(select(UserORM)).one().created_at
    assert stored == datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
    assert stored.tzinfo == UTC


def test_rejects_naive_datetimes(session: Session) -> None:
    naive = datetime(2026, 7, 1, 12, 0)
    session.add(
        UserORM(id=USER_ID, username="kana", created_at=naive, updated_at=naive)
    )
    with pytest.raises(StatementError, match="naive datetime"):
        session.flush()


def test_timestamps_have_no_database_default(session: Session) -> None:
    # They come from the domain entity; the database never invents them.
    session.add(UserORM(id=USER_ID, username="kana"))
    with pytest.raises(IntegrityError):
        session.flush()
