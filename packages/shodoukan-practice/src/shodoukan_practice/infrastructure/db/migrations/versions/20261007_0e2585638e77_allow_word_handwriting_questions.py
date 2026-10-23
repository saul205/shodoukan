"""Allow word handwriting questions

Questions of type `card.handwriting_word` (a word written a character per
cell) join the `type` check. Nothing else changes: what the type adds goes in
`details`, and handwriting exercises of words reuse `card.handwriting`
settings. Downgrading deletes what the old code can't read: those questions,
and the word handwriting exercises (their sessions stay, as for any deleted
exercise).

Revision ID: 0e2585638e77
Revises: 33f2afbdd7cf
Create Date: 2026-10-07 10:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0e2585638e77"
down_revision: str | Sequence[str] | None = "33f2afbdd7cf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Batch mode so SQLite (tests) can alter the check constraint too.

_exercises = sa.table(
    "exercises",
    sa.column("id", sa.Integer),
    sa.column("item_kind", sa.String),
    sa.column("settings", sa.JSON),
)


def upgrade() -> None:
    with op.batch_alter_table("exercise_questions") as batch:
        batch.drop_constraint(op.f("ck_exercise_questions_type"), type_="check")
        batch.create_check_constraint(
            op.f("ck_exercise_questions_type"),
            "type IN ('card.choice', 'card.handwriting', 'card.handwriting_word')",
        )


def downgrade() -> None:
    op.execute("DELETE FROM exercise_questions WHERE type = 'card.handwriting_word'")
    connection = op.get_bind()
    exercises = connection.execute(
        sa.select(_exercises.c.id, _exercises.c.item_kind, _exercises.c.settings)
    ).all()
    words = [
        id_
        for id_, item_kind, settings in exercises
        if item_kind == "entries" and settings["type"] == "card.handwriting"
    ]
    if words:
        connection.execute(_exercises.delete().where(_exercises.c.id.in_(words)))
    with op.batch_alter_table("exercise_questions") as batch:
        batch.drop_constraint(op.f("ck_exercise_questions_type"), type_="check")
        batch.create_check_constraint(
            op.f("ck_exercise_questions_type"),
            "type IN ('card.choice', 'card.handwriting')",
        )
