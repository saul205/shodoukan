"""Add notes to entries, senses and kanji

Nullable free text written by the user; existing rows get no note.

Revision ID: cc326135e923
Revises: 4ea69ccc76fd
Create Date: 2026-10-03 11:47:37.993622+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "cc326135e923"
down_revision: str | Sequence[str] | None = "4ea69ccc76fd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("practice_entries", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("practice_kanji", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("practice_senses", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("practice_senses", "notes")
    op.drop_column("practice_kanji", "notes")
    op.drop_column("practice_entries", "notes")
