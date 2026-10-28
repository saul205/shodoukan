"""The Alembic migrations build exactly the schema the ORM models describe."""

import json
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

from shodoukan_practice.infrastructure.db.orm import Base

ALEMBIC_INI = Path(__file__).parents[3] / "packages/shodoukan-practice/alembic.ini"


def test_migrations_match_models(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'practice.sqlite'}"
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)

    command.upgrade(config, "head")

    with create_engine(url).connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert diff == []


def test_migrations_downgrade_to_empty(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'practice.sqlite'}"
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)

    command.upgrade(config, "head")
    command.downgrade(config, "base")


def test_questions_move_their_options_into_details(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'practice.sqlite'}"
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "bfad9df5a138")
    engine = create_engine(url)
    options = [{"text": "た.べる", "item_id": 7}, {"text": "みず", "item_id": 8}]
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users VALUES "
                "('00000000000000000000000000000001', 'dev', :now, :now)"
            ),
            {"now": "2026-10-06 10:00:00"},
        )
        connection.execute(
            text(
                "INSERT INTO exercise_sessions VALUES (1, "
                "'00000000000000000000000000000001', NULL, 'N5', 'kanji', 'en', "
                ":now, :now, NULL)"
            ),
            {"now": "2026-10-06 10:00:00"},
        )
        connection.execute(
            text(
                "INSERT INTO exercise_questions (id, session_id, position, "
                "prompt_fields, answer_field, prompt, options, correct_option, back) "
                "VALUES (1, 1, 0, '[\"literal\"]', 'kunyomi', '[]', :options, 1, '[]')"
            ),
            {"options": json.dumps(options)},
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        type_, details = connection.execute(
            text("SELECT type, details FROM exercise_questions")
        ).one()
    assert type_ == "card.choice"
    assert json.loads(details) == {"options": options, "correct_option": 1}

    command.downgrade(config, "bfad9df5a138")
    with engine.connect() as connection:
        restored, correct = connection.execute(
            text("SELECT options, correct_option FROM exercise_questions")
        ).one()
    assert (json.loads(restored), correct) == (options, 1)


def test_downgrading_drops_what_the_old_code_cant_read(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'practice.sqlite'}"
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    now = {"now": "2026-10-06 10:00:00"}
    choice = {"type": "card.choice", "directions": [], "back_fields": []}
    drawing = {"type": "card.handwriting", "directions": [], "back_fields": []}
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users VALUES "
                "('00000000000000000000000000000001', 'dev', :now, :now)"
            ),
            now,
        )
        for id_, settings in [(1, choice), (2, drawing)]:
            connection.execute(
                text(
                    "INSERT INTO exercises VALUES (:id, "
                    "'00000000000000000000000000000001', 'N5', NULL, 'kanji', "
                    ":settings, :now, :now)"
                ),
                {"id": id_, "settings": json.dumps(settings), **now},
            )
        connection.execute(
            text(
                "INSERT INTO exercise_sessions VALUES (1, "
                "'00000000000000000000000000000001', 2, 'N5', 'kanji', 'en', "
                ":now, :now, NULL)"
            ),
            now,
        )
        connection.execute(
            text(
                "INSERT INTO exercise_questions (id, session_id, position, "
                "prompt_fields, answer_field, prompt, back, type, details) "
                "VALUES (1, 1, 0, '[\"meaning\"]', 'literal', '[]', '[]', "
                "'card.handwriting', '{}')"
            )
        )

    command.downgrade(config, "bfad9df5a138")

    with engine.connect() as connection:
        exercises = connection.execute(text("SELECT id FROM exercises")).all()
        questions = connection.execute(text("SELECT id FROM exercise_questions")).all()
        assert [row.id for row in exercises] == [1]
        assert questions == []


def test_examples_become_sentences(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'practice.sqlite'}"
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "c3a9f5e0d2b1")
    engine = create_engine(url)
    user = "00000000000000000000000000000001"
    now = "2026-10-20 10:00:00"
    with engine.begin() as connection:
        for sql in [
            f"INSERT INTO users VALUES ('{user}', 'dev', '{now}', '{now}')",
            "INSERT INTO practice_entries (id, user_id, source_entry_id, jlpt, "
            "is_common, is_active, dismissed_parts, created_at, updated_at) VALUES "
            f"(1, '{user}', 100, 5, 1, 1, '[]', '{now}', '{now}')",
            "INSERT INTO practice_entry_kanji_readings (entry_id, position, kanji, "
            "info, enabled, origin) VALUES (1, 0, '引く', '[]', 1, 'imported')",
            "INSERT INTO practice_senses (id, entry_id, position, pos, misc, "
            "dialects, info, enabled, origin) VALUES "
            "(10, 1, 0, '[]', '[]', '[]', '[]', 1, 'imported')",
            "INSERT INTO practice_examples (id, sense_id, position, text, enabled, "
            "origin, revision, source_collection_ids) VALUES "
            "(5, 10, 0, '引かれた', 1, 'imported', 0, '[]'), "
            "(6, 10, 1, '', 0, 'added', 2, '[]'), "
            "(7, 10, 2, '', 1, 'added', 0, '[4, \"file\"]')",
            "INSERT INTO practice_example_sentences (example_id, position, lang, "
            "text) VALUES (5, 0, 'jpn', 'カーテンがゆっくり引かれた。'), "
            "(5, 1, 'eng', 'The curtain was drawn.'), "
            "(6, 0, 'jpn', 'くじを引く。'), (7, 0, 'jpn', '風邪を引いた。')",
        ]:
            connection.execute(text(sql))

    command.upgrade(config, "37c04a6faa6f")

    with engine.connect() as connection:
        sentences = connection.execute(
            text(
                "SELECT s.id, s.text, s.is_active, s.origin, s.revision, "
                "s.source_collection_ids, w.span_start, w.span_end, w.entry_id, "
                "w.sense_id FROM practice_sentences s "
                "JOIN practice_sentence_words w ON w.sentence_id = s.id ORDER BY s.id"
            )
        ).all()
        translations = connection.execute(
            text("SELECT sentence_id, lang, text FROM practice_sentence_translations")
        ).all()
    assert [tuple(row) for row in sentences] == [
        # JMDict's form of the word, inflected, is the gap.
        (5, "カーテンがゆっくり引かれた。", 1, "imported", 0, "[]", 9, 13, 1, 10),
        # An own example: the spelling found as is; its state and version kept.
        (6, "くじを引く。", 0, "added", 2, "[]", 3, 5, 1, 10),
        # Not found as is: linked without a span.
        (7, "風邪を引いた。", 1, "added", 0, '[4, "file"]', None, None, 1, 10),
    ]
    assert [tuple(row) for row in translations] == [
        (5, "eng", "The curtain was drawn.")
    ]

    command.downgrade(config, "c3a9f5e0d2b1")
    with engine.connect() as connection:
        examples = connection.execute(text("SELECT id FROM practice_examples")).all()
    assert [row.id for row in examples] == [5, 6, 7]
