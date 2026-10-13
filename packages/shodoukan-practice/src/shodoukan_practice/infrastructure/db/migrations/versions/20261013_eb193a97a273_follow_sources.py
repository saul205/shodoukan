"""Follow sources

Updating an imported collection from its source must not bring back what
the user removed: the items they took out of a copy
(`*_collection_dismissed_items`, one row per collection and item key) and
the copied parts they deleted from a word or kanji (`dismissed_parts`, the
parts' kinds and identities as JSON, empty for existing rows). Parts with
content also get `revision`: an edit by the row that wrote a part is a new
version of it, so the owner's edits reach their copies (0 for existing
rows).

Revision ID: eb193a97a273
Revises: 34cc2ff80759
Create Date: 2026-10-13 12:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "eb193a97a273"
down_revision: str | Sequence[str] | None = "34cc2ff80759"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_KINDS = ("entry", "kanji")
_ITEM_TABLES = ("practice_entries", "practice_kanji")
_CONTENT_TABLES = (
    "practice_entry_kanji_readings",
    "practice_entry_readings",
    "practice_glosses",
    "practice_examples",
    "practice_kanji_meanings",
)

# Batch mode so SQLite (tests) can drop columns.


def upgrade() -> None:
    for kind in _KINDS:
        table = f"{kind}_collection_dismissed_items"
        op.create_table(
            table,
            sa.Column("collection_id", sa.Integer(), nullable=False),
            sa.Column("item_key", sa.String(length=64), nullable=False),
            sa.ForeignKeyConstraint(
                ["collection_id"],
                [f"{kind}_collections.id"],
                name=op.f(f"fk_{table}_collection_id_{kind}_collections"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint(
                "collection_id", "item_key", name=op.f(f"pk_{table}")
            ),
        )
    for table in _ITEM_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column(
                    "dismissed_parts", sa.JSON(), server_default="[]", nullable=False
                )
            )
    for table in _CONTENT_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column("revision", sa.Integer(), server_default="0", nullable=False)
            )


def downgrade() -> None:
    for table in _CONTENT_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("revision")
    for table in _ITEM_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("dismissed_parts")
    for kind in _KINDS:
        op.drop_table(f"{kind}_collection_dismissed_items")
