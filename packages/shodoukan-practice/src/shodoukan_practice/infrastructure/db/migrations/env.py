"""Alembic environment for the practice database.

The URL comes from `sqlalchemy.url` when a caller sets it programmatically
(tests), otherwise from PRACTICE_DATABASE_URL.
"""

from logging.config import fileConfig
from typing import Any, Literal

from alembic import context
from alembic.autogenerate.api import AutogenContext
from sqlalchemy import TypeDecorator, create_engine, pool

from shodoukan_practice.infrastructure.db.connection import database_url
from shodoukan_practice.infrastructure.db.orm import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or database_url()


def render_item(
    type_: str, obj: Any, autogen_context: AutogenContext
) -> str | Literal[False]:
    """Render custom column types (e.g. UtcDateTime) as their plain SQLAlchemy
    type, so migrations never import application code."""
    if type_ == "type" and isinstance(obj, TypeDecorator):
        return f"sa.{obj.impl!r}"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_item=render_item,
            # SQLite (tests) can't ALTER most things in place.
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
