"""Record where imported parts were copied from

Importing a collection (from a file, later from another user) copies the
origin's own parts. `copied_from_id` on each copyable part, and on
practice_entries for words of the user's own, keeps the origin element's id
so importing it again doesn't duplicate it; `copied_from_collection_id` does
the same for collections. No foreign keys: the origin may belong to another
user or database and be gone. Existing rows weren't copied (NULL).

Revision ID: b9ae9e057d9c
Revises: d1d520270eb8
Create Date: 2026-10-09 06:41:18.519755+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9ae9e057d9c"
down_revision: str | Sequence[str] | None = "d1d520270eb8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLLECTION_TABLES = ("entry_collections", "kanji_collections")
_PART_TABLES = (
    "practice_entries",
    "practice_entry_kanji_readings",
    "practice_entry_readings",
    "practice_senses",
    "practice_glosses",
    "practice_examples",
    "practice_kanji_meanings",
)


def upgrade() -> None:
    for table in _COLLECTION_TABLES:
        op.add_column(
            table, sa.Column("copied_from_collection_id", sa.Integer(), nullable=True)
        )
    for table in _PART_TABLES:
        op.add_column(table, sa.Column("copied_from_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    # Batch mode so SQLite (tests) can drop columns.
    for table in _PART_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("copied_from_id")
    for table in _COLLECTION_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("copied_from_collection_id")
