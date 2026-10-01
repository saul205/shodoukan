import sqlite3
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shodoukan import Dictionary
from shodoukan_practice.infrastructure.db.orm import Base, UserORM

# Make the local `factories` helper and the core `db_helpers` (tests/) importable.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[2]))

from db_helpers import SCHEMA, seed  # type: ignore[import-not-found]
from factories import TIMESTAMPS


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
    user = UserORM(username="saul", **TIMESTAMPS)
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def other_user(session: Session) -> UserORM:
    other = UserORM(username="other", **TIMESTAMPS)
    session.add(other)
    session.flush()
    return other


@pytest.fixture
def dictionary(tmp_path: Path) -> Iterator[Dictionary]:
    """A real shodoukan dictionary, seeded with the core library's test data."""
    path = tmp_path / "dictionary.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    seed(conn)
    conn.close()
    with Dictionary(db_path=path, auto_download=False) as dictionary:
        yield dictionary
