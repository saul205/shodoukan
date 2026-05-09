import os
import sqlite3
from pathlib import Path

_ENV_VAR = "SHODOUKAN_DB_PATH"
_DEFAULT = Path.home() / ".local" / "share" / "shodoukan" / "shodoukan.sqlite"


def resolve_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path)
    env = os.environ.get(_ENV_VAR)
    if env:
        return Path(env)
    return _DEFAULT


def open_connection(path: Path) -> sqlite3.Connection:
    uri = path.as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
