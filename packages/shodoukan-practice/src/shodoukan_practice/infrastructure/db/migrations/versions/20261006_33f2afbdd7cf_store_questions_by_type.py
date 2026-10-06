"""Store questions by type

Questions get a `type` (every existing one is a choice card) and `details`,
the JSON with what only that type has. A choice card's `options` and
`correct_option` move into `details`, so no column is left empty for the other
types. Downgrading moves them back and deletes the questions of other types
(handwriting), which the old schema can't hold.

Revision ID: 33f2afbdd7cf
Revises: bfad9df5a138
Create Date: 2026-10-06 10:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "33f2afbdd7cf"
down_revision: str | Sequence[str] | None = "bfad9df5a138"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Batch mode so SQLite (tests) can alter and drop columns too. Rows are moved
# in Python so the JSON is read and written the same way on both databases.

_questions = sa.table(
    "exercise_questions",
    sa.column("id", sa.Integer),
    sa.column("type", sa.String),
    sa.column("options", sa.JSON),
    sa.column("correct_option", sa.Integer),
    sa.column("details", sa.JSON),
)


def upgrade() -> None:
    with op.batch_alter_table("exercise_questions") as batch:
        batch.add_column(
            sa.Column(
                "type", sa.String(32), nullable=False, server_default="card.choice"
            )
        )
        batch.add_column(sa.Column("details", sa.JSON(), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        sa.select(_questions.c.id, _questions.c.options, _questions.c.correct_option)
    ).all()
    for id_, options, correct_option in rows:
        connection.execute(
            _questions.update()
            .where(_questions.c.id == id_)
            .values(details={"options": options, "correct_option": correct_option})
        )

    with op.batch_alter_table("exercise_questions") as batch:
        batch.alter_column("type", server_default=None)
        batch.alter_column("details", existing_type=sa.JSON(), nullable=False)
        batch.create_check_constraint(
            op.f("ck_exercise_questions_type"),
            "type IN ('card.choice', 'card.handwriting')",
        )
        batch.drop_column("options")
        batch.drop_column("correct_option")


def downgrade() -> None:
    op.execute("DELETE FROM exercise_questions WHERE type <> 'card.choice'")
    with op.batch_alter_table("exercise_questions") as batch:
        batch.add_column(sa.Column("options", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("correct_option", sa.Integer(), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.select(_questions.c.id, _questions.c.details)).all()
    for id_, details in rows:
        connection.execute(
            _questions.update()
            .where(_questions.c.id == id_)
            .values(
                options=details["options"], correct_option=details["correct_option"]
            )
        )

    with op.batch_alter_table("exercise_questions") as batch:
        batch.alter_column("options", existing_type=sa.JSON(), nullable=False)
        batch.alter_column("correct_option", existing_type=sa.Integer(), nullable=False)
        batch.drop_constraint(op.f("ck_exercise_questions_type"), type_="check")
        batch.drop_column("details")
        batch.drop_column("type")
