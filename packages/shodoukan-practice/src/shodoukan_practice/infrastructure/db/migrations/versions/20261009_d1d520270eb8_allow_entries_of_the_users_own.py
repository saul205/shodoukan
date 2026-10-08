"""Allow entries of the user's own

`practice_entries.source_entry_id` becomes nullable: a word the user created
has no dictionary entry behind it (the unique constraint on
`(user_id, source_entry_id)` lets any number of NULLs through). Spellings
and readings get `origin` (existing rows imported), so the user's own can be
told apart and removed. Downgrading deletes what the old code can't read:
the user's own entries, spellings and readings.

Revision ID: d1d520270eb8
Revises: 23728b417aff
Create Date: 2026-10-09 12:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d1d520270eb8"
down_revision: str | Sequence[str] | None = "23728b417aff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Batch mode so SQLite (tests) can alter columns and add check constraints.

_READING_TABLES = ("practice_entry_kanji_readings", "practice_entry_readings")


def upgrade() -> None:
    with op.batch_alter_table("practice_entries") as batch:
        batch.alter_column("source_entry_id", existing_type=sa.Integer(), nullable=True)
    for table in _READING_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column(
                    "origin",
                    sa.String(length=16),
                    server_default="imported",
                    nullable=False,
                )
            )
            batch.create_check_constraint(
                op.f(f"ck_{table}_origin"), "origin IN ('imported', 'added')"
            )


def downgrade() -> None:
    op.execute("DELETE FROM practice_entries WHERE source_entry_id IS NULL")
    for table in _READING_TABLES:
        op.execute(f"DELETE FROM {table} WHERE origin = 'added'")
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(op.f(f"ck_{table}_origin"), type_="check")
            batch.drop_column("origin")
    with op.batch_alter_table("practice_entries") as batch:
        batch.alter_column(
            "source_entry_id", existing_type=sa.Integer(), nullable=False
        )
