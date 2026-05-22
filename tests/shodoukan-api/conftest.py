import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Ensure both packages are importable from source
sys.path.insert(0, str(Path(__file__).parents[2] / "packages/shodoukan/src"))
sys.path.insert(0, str(Path(__file__).parents[2] / "packages/shodoukan-api/src"))

from shodoukan.dictionary import Dictionary
from shodoukan_api.app import create_app
from shodoukan_api.deps import dictionary_dep

# Reuse the same schema and seed from the library tests
_SCHEMA = """
CREATE TABLE entries (id INTEGER PRIMARY KEY, jlpt INTEGER);
CREATE TABLE kanji_readings (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER NOT NULL, kanji TEXT NOT NULL, priority TEXT NOT NULL DEFAULT '[]', info TEXT NOT NULL DEFAULT '[]');
CREATE INDEX idx_kanji_readings_entry ON kanji_readings(entry_id);
CREATE INDEX idx_kanji_readings_kanji ON kanji_readings(kanji);
CREATE TABLE readings (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER NOT NULL, text TEXT NOT NULL, no_kanji INTEGER NOT NULL DEFAULT 0, priority TEXT NOT NULL DEFAULT '[]', info TEXT NOT NULL DEFAULT '[]');
CREATE INDEX idx_readings_entry ON readings(entry_id);
CREATE INDEX idx_readings_text ON readings(text);
CREATE TABLE reading_restrictions (reading_id INTEGER NOT NULL, kanji_reading_id INTEGER NOT NULL, PRIMARY KEY (reading_id, kanji_reading_id));
CREATE TABLE senses (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER NOT NULL, pos TEXT NOT NULL DEFAULT '[]', misc TEXT NOT NULL DEFAULT '[]', dialects TEXT NOT NULL DEFAULT '[]', info TEXT NOT NULL DEFAULT '[]');
CREATE TABLE glosses (id INTEGER PRIMARY KEY AUTOINCREMENT, sense_id INTEGER NOT NULL, text TEXT NOT NULL, type TEXT, lang TEXT);
CREATE VIRTUAL TABLE glosses_fts USING fts5(text, content='glosses', content_rowid='id');
CREATE TRIGGER glosses_ai AFTER INSERT ON glosses BEGIN INSERT INTO glosses_fts(rowid, text) VALUES (new.id, new.text); END;
CREATE TABLE cross_references (id INTEGER PRIMARY KEY AUTOINCREMENT, sense_id INTEGER NOT NULL, reference TEXT NOT NULL, reading TEXT, sense_idx INTEGER);
CREATE TABLE examples (id INTEGER PRIMARY KEY AUTOINCREMENT, sense_id INTEGER NOT NULL, source_name TEXT NOT NULL, source_id TEXT, text TEXT NOT NULL);
CREATE TABLE example_sentences (id INTEGER PRIMARY KEY AUTOINCREMENT, example_id INTEGER NOT NULL, lang TEXT NOT NULL, text TEXT NOT NULL);
CREATE TABLE kanji (literal TEXT PRIMARY KEY, grade INTEGER, stroke_count INTEGER NOT NULL, freq INTEGER, jlpt INTEGER, on_readings TEXT NOT NULL DEFAULT '[]', kun_readings TEXT NOT NULL DEFAULT '[]', nanori TEXT NOT NULL DEFAULT '[]');
CREATE TABLE kanji_meanings (id INTEGER PRIMARY KEY AUTOINCREMENT, literal TEXT NOT NULL, text TEXT NOT NULL, lang TEXT NOT NULL DEFAULT 'en');
CREATE VIRTUAL TABLE kanji_meanings_fts USING fts5(text, content='kanji_meanings', content_rowid='id');
CREATE TRIGGER kanji_meanings_ai AFTER INSERT ON kanji_meanings BEGIN INSERT INTO kanji_meanings_fts(rowid, text) VALUES (new.id, new.text); END;
CREATE TABLE entry_kanji (entry_id INTEGER NOT NULL, literal TEXT NOT NULL, priority_score INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (entry_id, literal));
CREATE INDEX idx_entry_kanji_literal ON entry_kanji(literal);
"""


def _seed(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO entries VALUES (1000001, 5)")
    conn.execute("INSERT INTO kanji_readings(entry_id, kanji, priority) VALUES (1000001, '食べる', ?)", (json.dumps(["ichi1"]),))
    conn.execute("INSERT INTO readings(entry_id, text, priority) VALUES (1000001, 'たべる', ?)", (json.dumps(["ichi1"]),))
    sid = conn.execute("INSERT INTO senses(entry_id, pos) VALUES (1000001, ?)", (json.dumps(["verb"]),)).lastrowid
    conn.execute("INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to eat', 'eng')", (sid,))
    conn.execute("INSERT INTO entry_kanji VALUES (1000001, '食', 1000)")

    conn.execute("INSERT INTO entries VALUES (1000002, 4)")
    conn.execute("INSERT INTO kanji_readings(entry_id, kanji) VALUES (1000002, '水')")
    conn.execute("INSERT INTO readings(entry_id, text) VALUES (1000002, 'みず')")
    sid = conn.execute("INSERT INTO senses(entry_id, pos) VALUES (1000002, ?)", (json.dumps(["noun"]),)).lastrowid
    conn.execute("INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'water', 'eng')", (sid,))
    conn.execute("INSERT INTO entry_kanji VALUES (1000002, '水', 500)")

    conn.execute("INSERT INTO kanji VALUES ('食', 2, 9, 316, 4, ?, ?, '[]')", (json.dumps(["ショク"]), json.dumps(["た.べる"])))
    conn.execute("INSERT INTO kanji_meanings(literal, text, lang) VALUES ('食', 'eat', 'en')")
    conn.execute("INSERT INTO kanji VALUES ('水', 1, 4, 56, 4, ?, ?, '[]')", (json.dumps(["スイ"]), json.dumps(["みず"])))
    conn.execute("INSERT INTO kanji_meanings(literal, text, lang) VALUES ('水', 'water', 'en')")
    conn.commit()


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test.sqlite"
    raw = sqlite3.connect(str(db_file))
    raw.executescript(_SCHEMA)
    raw.row_factory = sqlite3.Row
    _seed(raw)
    raw.close()

    with patch("shodoukan.dictionary.download"):
        d = Dictionary(db_path=db_file, auto_download=False)

    app = create_app()
    app.dependency_overrides[dictionary_dep] = lambda: d

    with TestClient(app) as c:
        yield c

    d.close()
