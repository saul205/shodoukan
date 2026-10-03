import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[2] / "packages/shodoukan/src"))
sys.path.insert(0, str(Path(__file__).parents[2] / "packages/shodoukan-api/src"))
sys.path.insert(0, str(Path(__file__).parents[1]))

from db_helpers import SCHEMA, seed
from shodoukan.dictionary import Dictionary
from shodoukan_api.app import create_app
from shodoukan_api.deps import dictionary_dep


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test.sqlite"
    raw = sqlite3.connect(str(db_file))
    raw.executescript(SCHEMA)
    raw.row_factory = sqlite3.Row
    seed(raw)
    raw.close()

    with patch("shodoukan.dictionary.download"):
        d = Dictionary(db_path=db_file, auto_download=False)

    app = create_app()
    app.dependency_overrides[dictionary_dep] = lambda: d

    with TestClient(app) as c:
        yield c

    d.close()
