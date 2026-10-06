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
