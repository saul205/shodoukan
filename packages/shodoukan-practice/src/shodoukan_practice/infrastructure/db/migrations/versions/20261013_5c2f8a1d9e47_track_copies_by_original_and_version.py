"""Track copies by original and version

`copied_from_id` only remembered the row a copy came from, so a copy of a
copy lost its origin. A copy now records three ids (see
`shared_collection_value`): `original_id`, the part all its copies share;
`source_id`, the row it was copied from (the old `copied_from_id`); and, on
the parts with content (spellings, readings, glosses, examples, kanji
meanings), `edited_id`, the version of that content. Senses and words of the
user's own are containers: no version. `copied_from_collection_id` becomes
`source_collection_id`. Existing copies are their own original and version
(NULL), as nothing records their chain.

Revision ID: 5c2f8a1d9e47
Revises: b9ae9e057d9c
Create Date: 2026-10-13 09:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5c2f8a1d9e47"
down_revision: str | Sequence[str] | None = "b9ae9e057d9c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLLECTION_TABLES = ("entry_collections", "kanji_collections")
_CONTAINER_TABLES = ("practice_entries", "practice_senses")
_CONTENT_TABLES = (
    "practice_entry_kanji_readings",
    "practice_entry_readings",
    "practice_glosses",
    "practice_examples",
    "practice_kanji_meanings",
)

# Batch mode so SQLite (tests) can rename and drop columns.


def upgrade() -> None:
    for table in _COLLECTION_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.alter_column(
                "copied_from_collection_id",
                new_column_name="source_collection_id",
                existing_type=sa.Integer(),
                existing_nullable=True,
            )
    for table in (*_CONTAINER_TABLES, *_CONTENT_TABLES):
        with op.batch_alter_table(table) as batch:
            batch.alter_column(
                "copied_from_id",
                new_column_name="source_id",
                existing_type=sa.Integer(),
                existing_nullable=True,
            )
            batch.add_column(sa.Column("original_id", sa.Integer(), nullable=True))
            if table in _CONTENT_TABLES:
                batch.add_column(sa.Column("edited_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    for table in (*_CONTAINER_TABLES, *_CONTENT_TABLES):
        with op.batch_alter_table(table) as batch:
            if table in _CONTENT_TABLES:
                batch.drop_column("edited_id")
            batch.drop_column("original_id")
            batch.alter_column(
                "source_id",
                new_column_name="copied_from_id",
                existing_type=sa.Integer(),
                existing_nullable=True,
            )
    for table in _COLLECTION_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.alter_column(
                "source_collection_id",
                new_column_name="copied_from_collection_id",
                existing_type=sa.Integer(),
                existing_nullable=True,
            )
