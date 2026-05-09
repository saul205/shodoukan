import os
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

_ENV_VAR = "SHODOUKAN_DB_PATH"
_DEFAULT = Path.home() / ".local" / "share" / "shodoukan" / "shodoukan.sqlite"


def resolve_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path)
    env = os.environ.get(_ENV_VAR)
    if env:
        return Path(env)
    return _DEFAULT


def open_connection(path: Path) -> Engine:
    def _creator() -> sqlite3.Connection:
        return sqlite3.connect(
            f"file:{path}?mode=ro", uri=True, check_same_thread=False
        )

    return create_engine("sqlite://", creator=_creator)


def open_test_connection(raw: sqlite3.Connection) -> Engine:
    return create_engine(
        "sqlite://",
        creator=lambda: raw,
        poolclass=StaticPool,
    )
