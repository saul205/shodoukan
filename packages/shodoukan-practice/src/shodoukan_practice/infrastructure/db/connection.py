"""Read-write engine/session for the practice database.

The URL comes only from the process environment (`PRACTICE_DATABASE_URL`);
there is no default so credentials never live in code. Loading an env file
(e.g. `.env.dev`) is the job of whoever starts the process.
"""

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL_ENV = "PRACTICE_DATABASE_URL"


def database_url() -> str:
    url = os.environ.get(DATABASE_URL_ENV)
    if not url:
        raise RuntimeError(
            f"{DATABASE_URL_ENV} is not set; see .env.example for its format"
        )
    return url


def create_db_engine(url: str | None = None) -> Engine:
    return create_engine(url or database_url(), pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
