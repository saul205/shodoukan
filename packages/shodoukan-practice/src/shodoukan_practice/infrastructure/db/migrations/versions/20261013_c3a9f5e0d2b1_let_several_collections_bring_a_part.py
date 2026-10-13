"""Let several collections bring a part

A copied part recorded the one collection it came with
(`source_collection_id`), so updating one copy could remove a part another
followed collection still brings. It now records every collection that brings
it (`source_collection_ids`, JSON); an update lets go of its own, and the part
goes only when none is left. Existing values become one-element lists.

Revision ID: c3a9f5e0d2b1
Revises: 7d4e1c2b9a60
Create Date: 2026-10-13 15:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3a9f5e0d2b1"
down_revision: str | Sequence[str] | None = "7d4e1c2b9a60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONTENT_TABLES = (
    "practice_entry_kanji_readings",
    "practice_entry_readings",
    "practice_glosses",
    "practice_examples",
    "practice_kanji_meanings",
)

# Batch mode so SQLite (tests) can drop columns; the JSON functions differ.


def _postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    to_list = "json_build_array" if _postgresql() else "json_array"
    for table in _CONTENT_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column(
                    "source_collection_ids",
                    sa.JSON(),
                    server_default="[]",
                    nullable=False,
                )
            )
        op.execute(
            f"UPDATE {table} SET source_collection_ids = "
            f"{to_list}(source_collection_id) WHERE source_collection_id IS NOT NULL"
        )
        with op.batch_alter_table(table) as batch:
            batch.drop_column("source_collection_id")


def downgrade() -> None:
    first = (
        "(source_collection_ids->>0)::integer"
        if _postgresql()
        else "json_extract(source_collection_ids, '$[0]')"
    )
    for table in _CONTENT_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column("source_collection_id", sa.Integer(), nullable=True)
            )
        op.execute(f"UPDATE {table} SET source_collection_id = {first}")
        with op.batch_alter_table(table) as batch:
            batch.drop_column("source_collection_ids")
