"""Share collections

A collection can be published: `is_public`, `published_version` and
`published_at` on the collection, and its latest snapshot (the #86 payload)
in `*_collection_publications`, one row per collection. Imports from a
public collection record who downloaded which version
(`*_collection_downloads`, one row per user) and what an update from the
source will need: `source_version` on the copy, `from_source` on its
membership, and `source_collection_id` on the parts with content it copied.
Existing rows weren't published or imported from a public collection.

Revision ID: 34cc2ff80759
Revises: 5c2f8a1d9e47
Create Date: 2026-10-13 10:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "34cc2ff80759"
down_revision: str | Sequence[str] | None = "5c2f8a1d9e47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_KINDS = ("entry", "kanji")
_CONTENT_TABLES = (
    "practice_entry_kanji_readings",
    "practice_entry_readings",
    "practice_glosses",
    "practice_examples",
    "practice_kanji_meanings",
)

# Batch mode so SQLite (tests) can alter and drop columns.


def upgrade() -> None:
    for kind in _KINDS:
        collections = f"{kind}_collections"
        with op.batch_alter_table(collections) as batch:
            batch.add_column(
                sa.Column(
                    "is_public",
                    sa.Boolean(),
                    server_default=sa.text("false"),
                    nullable=False,
                )
            )
            batch.add_column(
                sa.Column(
                    "published_version",
                    sa.Integer(),
                    server_default="0",
                    nullable=False,
                )
            )
            batch.add_column(sa.Column("published_at", sa.DateTime(), nullable=True))
            batch.add_column(sa.Column("source_version", sa.Integer(), nullable=True))
        with op.batch_alter_table(f"{kind}_collection_items") as batch:
            batch.add_column(
                sa.Column(
                    "from_source",
                    sa.Boolean(),
                    server_default=sa.text("false"),
                    nullable=False,
                )
            )
        op.create_table(
            f"{kind}_collection_publications",
            sa.Column("collection_id", sa.Integer(), nullable=False),
            sa.Column("item_count", sa.Integer(), nullable=False),
            sa.Column("includes_notes", sa.Boolean(), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.ForeignKeyConstraint(
                ["collection_id"],
                [f"{collections}.id"],
                name=op.f(
                    f"fk_{kind}_collection_publications_collection_id_{collections}"
                ),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint(
                "collection_id", name=op.f(f"pk_{kind}_collection_publications")
            ),
        )
        downloads = f"{kind}_collection_downloads"
        op.create_table(
            downloads,
            sa.Column("collection_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("downloaded_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["collection_id"],
                [f"{collections}.id"],
                name=op.f(f"fk_{downloads}_collection_id_{collections}"),
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name=op.f(f"fk_{downloads}_user_id_users"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint(
                "collection_id", "user_id", name=op.f(f"pk_{downloads}")
            ),
        )
        op.create_index(op.f(f"ix_{downloads}_user_id"), downloads, ["user_id"])
    for table in _CONTENT_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column("source_collection_id", sa.Integer(), nullable=True)
            )


def downgrade() -> None:
    for table in _CONTENT_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("source_collection_id")
    for kind in _KINDS:
        downloads = f"{kind}_collection_downloads"
        op.drop_index(op.f(f"ix_{downloads}_user_id"), table_name=downloads)
        op.drop_table(downloads)
        op.drop_table(f"{kind}_collection_publications")
        with op.batch_alter_table(f"{kind}_collection_items") as batch:
            batch.drop_column("from_source")
        with op.batch_alter_table(f"{kind}_collections") as batch:
            batch.drop_column("source_version")
            batch.drop_column("published_at")
            batch.drop_column("published_version")
            batch.drop_column("is_public")
