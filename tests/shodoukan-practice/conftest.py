import sqlite3
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shodoukan import Dictionary
from shodoukan_practice.api.app import create_app
from shodoukan_practice.api.auth import TokenVerifier
from shodoukan_practice.api.deps import (
    get_dictionary_gateway,
    get_session,
    get_token_verifier,
)
from shodoukan_practice.infrastructure.db.orm import Base, UserORM
from shodoukan_practice.infrastructure.dictionary import ShodoukanDictionaryGateway

# Make the local helpers (`factories`, `tokens`) and the core `db_helpers` importable.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1]))

from db_helpers import SCHEMA, seed  # type: ignore[import-not-found]
from factories import OTHER_USER_ID, TIMESTAMPS, USER_ID
from tokens import DEFAULT_SUBJECT, ISSUER, TokenFactory


@pytest.fixture
def engine() -> Engine:
    # StaticPool: every session shares the same in-memory database.
    # check_same_thread=False: the API tests' TestClient runs endpoints in a
    # worker thread; the single shared connection is still used sequentially.
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection: Any, _: Any) -> None:
        # SQLite ignores FKs (and so ON DELETE CASCADE) unless asked.
        dbapi_connection.execute("PRAGMA foreign_keys = ON")
        # Let SQLAlchemy emit BEGIN itself: pysqlite's own transaction
        # handling breaks SAVEPOINTs (Session.begin_nested).
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin(connection: Any) -> None:
        connection.exec_driver_sql("BEGIN")

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def user(session: Session) -> UserORM:
    user = UserORM(id=USER_ID, username="saul", **TIMESTAMPS)
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def other_user(session: Session) -> UserORM:
    other = UserORM(id=OTHER_USER_ID, username="other", **TIMESTAMPS)
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


# --- API ---


@pytest.fixture(scope="session")
def signing_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def make_token(signing_key: rsa.RSAPrivateKey) -> TokenFactory:
    def _make(
        subject: str = DEFAULT_SUBJECT,
        *,
        issuer: str = ISSUER,
        expires_in: timedelta = timedelta(minutes=5),
        key: rsa.RSAPrivateKey | None = None,
        **claims: Any,
    ) -> str:
        payload = {
            "sub": subject,
            "iss": issuer,
            "exp": datetime.now(UTC) + expires_in,
            **claims,
        }
        return jwt.encode(payload, key or signing_key, algorithm="RS256")

    return _make


@pytest.fixture
def verifier(signing_key: rsa.RSAPrivateKey) -> TokenVerifier:
    public_key = signing_key.public_key()
    return TokenVerifier(
        issuer=ISSUER, audience=None, key_for_token=lambda _: public_key
    )


@pytest.fixture
def client(
    session: Session, dictionary: Dictionary, verifier: TokenVerifier
) -> Iterator[TestClient]:
    app = create_app()

    def _session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_dictionary_gateway] = lambda: (
        ShodoukanDictionaryGateway(dictionary)
    )
    app.dependency_overrides[get_token_verifier] = lambda: verifier
    with TestClient(app) as client:
        yield client
