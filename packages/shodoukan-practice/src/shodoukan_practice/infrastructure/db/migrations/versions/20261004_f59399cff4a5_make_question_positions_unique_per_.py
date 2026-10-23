"""Make question positions unique per session

Two answers to the same session racing to store the next question can't
both store one at the same position.

Revision ID: f59399cff4a5
Revises: 08d07b56c263
Create Date: 2026-10-04 18:42:22.386628+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f59399cff4a5"
down_revision: str | Sequence[str] | None = "08d07b56c263"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Batch mode so SQLite (tests) can add and drop the constraint too.


def upgrade() -> None:
    with op.batch_alter_table("exercise_questions") as batch:
        batch.create_unique_constraint(
            op.f("uq_exercise_questions_session_id_position"),
            ["session_id", "position"],
        )


def downgrade() -> None:
    with op.batch_alter_table("exercise_questions") as batch:
        batch.drop_constraint(
            op.f("uq_exercise_questions_session_id_position"), type_="unique"
        )
