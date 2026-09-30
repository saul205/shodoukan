from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shodoukan_practice.infrastructure.db.orm import Base, UserORM


@pytest.fixture
def engine() -> Engine:
    # StaticPool: every session shares the same in-memory database.
    engine = create_engine("sqlite://", poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection: Any, _: Any) -> None:
        # SQLite ignores FKs (and so ON DELETE CASCADE) unless asked.
        dbapi_connection.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def user(session: Session) -> UserORM:
    user = UserORM(username="saul")
    session.add(user)
    session.flush()
    return user
