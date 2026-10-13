"""Version edits by revision

A part's version was the row that wrote it (`edited_id`, or its own id), so
an owner editing their own original part left its version unchanged and the
edit never reached the copies. Parts with content get `revision`, raised by
every edit: the version is the row and its revision. Existing rows are
revision 0.

Revision ID: 7d4e1c2b9a60
Revises: eb193a97a273
Create Date: 2026-10-13 13:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7d4e1c2b9a60"
down_revision: str | Sequence[str] | None = "eb193a97a273"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONTENT_TABLES = (
    "practice_entry_kanji_readings",
    "practice_entry_readings",
    "practice_glosses",
    "practice_examples",
    "practice_kanji_meanings",
)

# Batch mode so SQLite (tests) can drop columns.


def upgrade() -> None:
    for table in _CONTENT_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column("revision", sa.Integer(), server_default="0", nullable=False)
            )


def downgrade() -> None:
    for table in _CONTENT_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("revision")
