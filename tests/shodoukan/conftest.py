import json
import sqlite3

import pytest

_SCHEMA = """
CREATE TABLE entries (id INTEGER PRIMARY KEY);

CREATE TABLE kanji_readings (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    kanji    TEXT    NOT NULL,
    priority TEXT    NOT NULL DEFAULT '[]',
    info     TEXT    NOT NULL DEFAULT '[]'
);
CREATE INDEX idx_kanji_readings_entry ON kanji_readings(entry_id);
CREATE INDEX idx_kanji_readings_kanji ON kanji_readings(kanji);

CREATE TABLE readings (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    text     TEXT    NOT NULL,
    no_kanji INTEGER NOT NULL DEFAULT 0,
    priority TEXT    NOT NULL DEFAULT '[]',
    info     TEXT    NOT NULL DEFAULT '[]'
);
CREATE INDEX idx_readings_entry ON readings(entry_id);
CREATE INDEX idx_readings_text  ON readings(text);

CREATE TABLE reading_restrictions (
    reading_id       INTEGER NOT NULL REFERENCES readings(id),
    kanji_reading_id INTEGER NOT NULL REFERENCES kanji_readings(id),
    PRIMARY KEY (reading_id, kanji_reading_id)
);

CREATE TABLE senses (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    pos      TEXT    NOT NULL DEFAULT '[]',
    misc     TEXT    NOT NULL DEFAULT '[]',
    dialects TEXT    NOT NULL DEFAULT '[]',
    info     TEXT    NOT NULL DEFAULT '[]'
);

CREATE TABLE glosses (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    sense_id INTEGER NOT NULL REFERENCES senses(id),
    text     TEXT    NOT NULL,
    type     TEXT,
    lang     TEXT
);

CREATE VIRTUAL TABLE glosses_fts USING fts5(
    text,
    content='glosses',
    content_rowid='id'
);

CREATE TRIGGER glosses_ai AFTER INSERT ON glosses BEGIN
    INSERT INTO glosses_fts(rowid, text) VALUES (new.id, new.text);
END;

CREATE TABLE cross_references (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    sense_id  INTEGER NOT NULL REFERENCES senses(id),
    reference TEXT    NOT NULL,
    reading   TEXT,
    sense_idx INTEGER
);

CREATE TABLE examples (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sense_id    INTEGER NOT NULL REFERENCES senses(id),
    source_name TEXT    NOT NULL,
    source_id   TEXT,
    text        TEXT    NOT NULL
);

CREATE TABLE example_sentences (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    example_id INTEGER NOT NULL REFERENCES examples(id),
    lang       TEXT    NOT NULL,
    text       TEXT    NOT NULL
);

CREATE TABLE kanji (
    literal      TEXT    PRIMARY KEY,
    grade        INTEGER,
    stroke_count INTEGER NOT NULL,
    freq         INTEGER,
    jlpt         INTEGER,
    on_readings  TEXT    NOT NULL DEFAULT '[]',
    kun_readings TEXT    NOT NULL DEFAULT '[]',
    nanori       TEXT    NOT NULL DEFAULT '[]'
);

CREATE TABLE kanji_meanings (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    literal TEXT    NOT NULL REFERENCES kanji(literal),
    text    TEXT    NOT NULL,
    lang    TEXT    NOT NULL DEFAULT 'en'
);

CREATE VIRTUAL TABLE kanji_meanings_fts USING fts5(
    text,
    content='kanji_meanings',
    content_rowid='id'
);

CREATE TRIGGER kanji_meanings_ai AFTER INSERT ON kanji_meanings BEGIN
    INSERT INTO kanji_meanings_fts(rowid, text) VALUES (new.id, new.text);
END;

CREATE TABLE entry_kanji (
    entry_id       INTEGER NOT NULL REFERENCES entries(id),
    literal        TEXT    NOT NULL,
    priority_score INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (entry_id, literal)
);
CREATE INDEX idx_entry_kanji_literal ON entry_kanji(literal);
"""


def _seed(conn: sqlite3.Connection) -> None:
    # Entry 1000001: 食べる (to eat)
    conn.execute("INSERT INTO entries VALUES (1000001)")
    conn.execute("INSERT INTO kanji_readings(entry_id, kanji, priority) VALUES (1000001, '食べる', ?)", (json.dumps(["ichi1"]),))
    conn.execute("INSERT INTO readings(entry_id, text, priority) VALUES (1000001, 'たべる', ?)", (json.dumps(["ichi1"]),))
    sense_id = conn.execute("INSERT INTO senses(entry_id, pos) VALUES (1000001, ?)", (json.dumps(["verb"]),)).lastrowid
    conn.execute("INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to eat', 'eng')", (sense_id,))
    conn.execute("INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to have a meal', 'eng')", (sense_id,))
    conn.execute("INSERT INTO entry_kanji(entry_id, literal, priority_score) VALUES (1000001, '食', 1000)")
    conn.execute("INSERT INTO entry_kanji(entry_id, literal, priority_score) VALUES (1000001, '食べる', 1000)")

    # Entry 1000002: 水 (water)
    conn.execute("INSERT INTO entries VALUES (1000002)")
    conn.execute("INSERT INTO kanji_readings(entry_id, kanji) VALUES (1000002, '水')")
    conn.execute("INSERT INTO readings(entry_id, text) VALUES (1000002, 'みず')")
    sense_id = conn.execute("INSERT INTO senses(entry_id, pos) VALUES (1000002, ?)", (json.dumps(["noun"]),)).lastrowid
    conn.execute("INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'water', 'eng')", (sense_id,))
    conn.execute("INSERT INTO entry_kanji(entry_id, literal, priority_score) VALUES (1000002, '水', 500)")

    # Entry 1000003: no-kanji entry (ありがとう)
    conn.execute("INSERT INTO entries VALUES (1000003)")
    conn.execute("INSERT INTO readings(entry_id, text, no_kanji) VALUES (1000003, 'ありがとう', 1)")
    sense_id = conn.execute("INSERT INTO senses(entry_id, pos) VALUES (1000003, ?)", (json.dumps(["interjection"]),)).lastrowid
    conn.execute("INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'thank you', 'eng')", (sense_id,))

    # Kanji: 食
    conn.execute(
        "INSERT INTO kanji(literal, grade, stroke_count, freq, jlpt, on_readings, kun_readings) VALUES ('食', 2, 9, 316, 4, ?, ?)",
        (json.dumps(["ショク", "ジキ"]), json.dumps(["た.べる", "た.う", "くら.う"])),
    )
    conn.execute("INSERT INTO kanji_meanings(literal, text, lang) VALUES ('食', 'eat', 'en')")
    conn.execute("INSERT INTO kanji_meanings(literal, text, lang) VALUES ('食', 'food', 'en')")

    # Kanji: 水
    conn.execute(
        "INSERT INTO kanji(literal, grade, stroke_count, freq, jlpt, on_readings, kun_readings) VALUES ('水', 1, 4, 56, 4, ?, ?)",
        (json.dumps(["スイ"]), json.dumps(["みず"])),
    )
    conn.execute("INSERT INTO kanji_meanings(literal, text, lang) VALUES ('水', 'water', 'en')")

    conn.commit()


@pytest.fixture
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.executescript(_SCHEMA)
    c.row_factory = sqlite3.Row
    _seed(c)
    return c
