"""Allow sentence questions

Questions of type `sentence.choice` (a word asked in one of its sentences)
join the `type` check. Nothing else changes: what the type adds goes in
`details`, and the exercises' settings are JSON. Downgrading deletes what the
old code can't read: those questions, and the sentence exercises (their
sessions stay, as for any deleted exercise).

Revision ID: 5e8b3c71a4d2
Revises: d0c3e71ccd60
Create Date: 2026-10-29 10:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5e8b3c71a4d2"
down_revision: str | Sequence[str] | None = "d0c3e71ccd60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Batch mode so SQLite (tests) can alter the check constraint too.

_exercises = sa.table(
    "exercises",
    sa.column("id", sa.Integer),
    sa.column("settings", sa.JSON),
)


def upgrade() -> None:
    with op.batch_alter_table("exercise_questions") as batch:
        batch.drop_constraint(op.f("ck_exercise_questions_type"), type_="check")
        batch.create_check_constraint(
            op.f("ck_exercise_questions_type"),
            "type IN ('card.choice', 'card.handwriting', 'card.handwriting_word', "
            "'sentence.choice')",
        )


def downgrade() -> None:
    op.execute("DELETE FROM exercise_questions WHERE type = 'sentence.choice'")
    connection = op.get_bind()
    exercises = connection.execute(
        sa.select(_exercises.c.id, _exercises.c.settings)
    ).all()
    sentences = [
        id_ for id_, settings in exercises if settings["type"] == "sentence.choice"
    ]
    if sentences:
        connection.execute(_exercises.delete().where(_exercises.c.id.in_(sentences)))
    with op.batch_alter_table("exercise_questions") as batch:
        batch.drop_constraint(op.f("ck_exercise_questions_type"), type_="check")
        batch.create_check_constraint(
            op.f("ck_exercise_questions_type"),
            "type IN ('card.choice', 'card.handwriting', 'card.handwriting_word')",
        )
