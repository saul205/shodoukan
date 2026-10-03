"""The Alembic migrations build exactly the schema the ORM models describe."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

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
