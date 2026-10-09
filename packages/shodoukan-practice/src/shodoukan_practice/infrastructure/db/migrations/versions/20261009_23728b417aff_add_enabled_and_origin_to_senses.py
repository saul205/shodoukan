"""Add enabled and origin to senses

Senses can be disabled (`enabled`, existing rows enabled) and users can add
their own (`origin`, existing rows imported). Downgrading deletes the
user's own senses, with their meanings and examples: the old code reads
every sense as the dictionary's.

Revision ID: 23728b417aff
Revises: 0e2585638e77
Create Date: 2026-10-09 10:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "23728b417aff"
down_revision: str | Sequence[str] | None = "0e2585638e77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Batch mode so SQLite (tests) can add the check constraint too.


def upgrade() -> None:
    with op.batch_alter_table("practice_senses") as batch:
        batch.add_column(
            sa.Column(
                "enabled",
                sa.Boolean(),
                server_default=sa.text("true"),
                nullable=False,
            )
        )
        batch.add_column(
            sa.Column(
                "origin",
                sa.String(length=16),
                server_default="imported",
                nullable=False,
            )
        )
        batch.create_check_constraint(
            op.f("ck_practice_senses_origin"), "origin IN ('imported', 'added')"
        )


def downgrade() -> None:
    op.execute("DELETE FROM practice_senses WHERE origin = 'added'")
    with op.batch_alter_table("practice_senses") as batch:
        batch.drop_constraint(op.f("ck_practice_senses_origin"), type_="check")
        batch.drop_column("origin")
        batch.drop_column("enabled")
