import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from db_helpers import SCHEMA, seed


@pytest.fixture
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA)
    c.row_factory = sqlite3.Row
    seed(c)
    return c


@pytest.fixture
def engine(conn):
    from shodoukan.db.connection import open_test_connection

    return open_test_connection(conn)
