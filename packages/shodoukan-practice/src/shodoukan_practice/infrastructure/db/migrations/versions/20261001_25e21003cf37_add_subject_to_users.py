"""Add subject to users

Revision ID: 25e21003cf37
Revises: 2021fc7c6163
Create Date: 2026-10-01 22:05:18.009383+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "25e21003cf37"
down_revision: str | Sequence[str] | None = "2021fc7c6163"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NOT NULL without a default is safe: no user can exist yet (there is no
    # registration flow before this revision). Batch mode: plain ALTERs on
    # PostgreSQL, a table rebuild on SQLite (used by the tests).
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("subject", sa.String(length=255), nullable=False))
        batch.create_unique_constraint(op.f("uq_users_subject"), ["subject"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint(op.f("uq_users_subject"), type_="unique")
        batch.drop_column("subject")
