import json
import sqlite3

SCHEMA = """
CREATE TABLE entries (
    id         INTEGER PRIMARY KEY,
    jlpt       INTEGER,
    freq_score INTEGER NOT NULL DEFAULT 0,
    has_common INTEGER NOT NULL DEFAULT 0
);

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
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id    INTEGER NOT NULL REFERENCES entries(id),
    sense_index INTEGER NOT NULL DEFAULT 0,
    pos         TEXT    NOT NULL DEFAULT '[]',
    misc        TEXT    NOT NULL DEFAULT '[]',
    dialects    TEXT    NOT NULL DEFAULT '[]',
    info        TEXT    NOT NULL DEFAULT '[]'
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
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    literal  TEXT    NOT NULL,
    PRIMARY KEY (entry_id, literal)
);
CREATE INDEX idx_entry_kanji_literal ON entry_kanji(literal);

CREATE TABLE entry_sense_counts (
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    lang     TEXT    NOT NULL,
    count    INTEGER NOT NULL,
    PRIMARY KEY (entry_id, lang)
);
CREATE INDEX idx_entry_sense_counts_entry ON entry_sense_counts(entry_id);

CREATE TABLE sense_lang_index (
    sense_id         INTEGER NOT NULL REFERENCES senses(id),
    lang             TEXT    NOT NULL,
    lang_sense_index INTEGER NOT NULL,
    PRIMARY KEY (sense_id, lang)
);
CREATE INDEX idx_sense_lang_index_sense ON sense_lang_index(sense_id);

CREATE TABLE kanji_svg (
    literal TEXT PRIMARY KEY,
    svg     TEXT NOT NULL
);
"""


def kanjivg_svg(literal: str, strokes: list[tuple[int, str]]) -> str:
    """A KanjiVG-style drawing: XML declaration, internal DTD, `kvg:` attributes.

    `strokes` are `(number, path)` pairs, written in the given order; each gets
    its number label at `(number, number)`.
    """
    code = f"{ord(literal):05x}"
    paths = "".join(
        f'<path id="kvg:{code}-s{n}" kvg:type="㇐" d="{d}"/>' for n, d in strokes
    )
    labels = "".join(
        f'<text transform="matrix(1 0 0 1 {n}.50 {n}.00)">{n}</text>'
        for n, _ in strokes
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!-- KanjiVG test drawing -->\n"
        '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN" '
        '"http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd" [\n'
        '<!ATTLIST g xmlns:kvg CDATA #FIXED "http://kanjivg.tagaini.net" '
        "kvg:element CDATA #IMPLIED >\n"
        '<!ATTLIST path xmlns:kvg CDATA #FIXED "http://kanjivg.tagaini.net" '
        "kvg:type CDATA #IMPLIED >\n"
        "]>\n"
        '<svg xmlns="http://www.w3.org/2000/svg" width="109" height="109" '
        'viewBox="0 0 109 109" xmlns:kvg="https://kanjivg.tagaini.net/">'
        f'<g id="kvg:StrokePaths_{code}" style="fill:none;stroke:#000000;">'
        f'<g id="kvg:{code}" kvg:element="{literal}">{paths}</g></g>'
        f'<g id="kvg:StrokeNumbers_{code}" style="font-size:8;">{labels}</g>'
        "</svg>"
    )


def seed(conn: sqlite3.Connection) -> None:
    # Entry 1000001: 食べる (to eat) — ichi1 on kanji+reading → freq_score=520
    conn.execute("INSERT INTO entries VALUES (1000001, 5, 520, 1)")
    conn.execute(
        "INSERT INTO kanji_readings(entry_id, kanji, priority)"
        " VALUES (1000001, '食べる', ?)",
        (json.dumps(["ichi1"]),),
    )
    conn.execute(
        "INSERT INTO readings(entry_id, text, priority) VALUES (1000001, 'たべる', ?)",
        (json.dumps(["ichi1"]),),
    )
    sense_id = conn.execute(
        "INSERT INTO senses(entry_id, pos) VALUES (1000001, ?)",
        (json.dumps(["verb"]),),
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to eat', 'eng')",
        (sense_id,),
    )
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to have a meal', 'eng')",
        (sense_id,),
    )
    conn.execute("INSERT INTO entry_kanji(entry_id, literal) VALUES (1000001, '食')")
    conn.execute("INSERT INTO entry_sense_counts VALUES (1000001, 'eng', 1)")
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sense_id,))

    # Entry 1000002: 水 (water) — no priority
    conn.execute("INSERT INTO entries VALUES (1000002, 4, 0, 0)")
    conn.execute("INSERT INTO kanji_readings(entry_id, kanji) VALUES (1000002, '水')")
    conn.execute("INSERT INTO readings(entry_id, text) VALUES (1000002, 'みず')")
    sense_id = conn.execute(
        "INSERT INTO senses(entry_id, pos) VALUES (1000002, ?)",
        (json.dumps(["noun"]),),
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'water', 'eng')",
        (sense_id,),
    )
    conn.execute("INSERT INTO entry_kanji(entry_id, literal) VALUES (1000002, '水')")
    conn.execute("INSERT INTO entry_sense_counts VALUES (1000002, 'eng', 1)")
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sense_id,))

    # Entry 1000003: no-kanji entry (ありがとう)
    conn.execute("INSERT INTO entries VALUES (1000003, NULL, 0, 0)")
    conn.execute(
        "INSERT INTO readings(entry_id, text, no_kanji)"
        " VALUES (1000003, 'ありがとう', 1)"
    )
    sense_id = conn.execute(
        "INSERT INTO senses(entry_id, pos) VALUES (1000003, ?)",
        (json.dumps(["interjection"]),),
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'thank you', 'eng')",
        (sense_id,),
    )
    conn.execute("INSERT INTO entry_sense_counts VALUES (1000003, 'eng', 1)")
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sense_id,))

    # Kanji: 食
    conn.execute(
        "INSERT INTO kanji(literal, grade, stroke_count, freq, jlpt,"
        " on_readings, kun_readings) VALUES ('食', 2, 9, 316, 4, ?, ?)",
        (json.dumps(["ショク", "ジキ"]), json.dumps(["た.べる", "た.う", "くら.う"])),
    )
    conn.execute(
        "INSERT INTO kanji_meanings(literal, text, lang) VALUES ('食', 'eat', 'en')"
    )
    conn.execute(
        "INSERT INTO kanji_meanings(literal, text, lang) VALUES ('食', 'food', 'en')"
    )

    # Kanji: 水
    conn.execute(
        "INSERT INTO kanji(literal, grade, stroke_count, freq, jlpt,"
        " on_readings, kun_readings) VALUES ('水', 1, 4, 56, 4, ?, ?)",
        (json.dumps(["スイ"]), json.dumps(["みず"])),
    )
    conn.execute(
        "INSERT INTO kanji_meanings(literal, text, lang) VALUES ('水', 'water', 'en')"
    )

    # Stroke order (KanjiVG): 食, with its strokes out of order in the document,
    # and 神 (U+795E), which isn't in `kanji`. 水 has no drawing.
    conn.execute(
        "INSERT INTO kanji_svg VALUES ('食', ?)",
        (
            kanjivg_svg(
                "食", [(2, "M20,30c10,0,20,0,30,0"), (1, "M54,10c0,5-20,20-40,25")]
            ),
        ),
    )
    conn.execute(
        "INSERT INTO kanji_svg VALUES ('\u795e', ?)",
        (kanjivg_svg("\u795e", [(1, "M30,10c2,2,4,6,4,9")]),),
    )

    conn.commit()
