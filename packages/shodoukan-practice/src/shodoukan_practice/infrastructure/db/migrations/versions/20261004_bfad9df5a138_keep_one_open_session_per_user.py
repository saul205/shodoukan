"""Keep one open session per user

A user studies one exercise session at a time. Before the partial unique
index, extra open sessions are closed the way the app closes a left session:
all but each user's latest end at their last activity, and their unanswered
active question is dropped. Downgrading only drops the index.

Revision ID: bfad9df5a138
Revises: f59399cff4a5
Create Date: 2026-10-04 19:56:45.961001+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "bfad9df5a138"
down_revision: str | Sequence[str] | None = "f59399cff4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE exercise_sessions SET finished_at = updated_at
        WHERE finished_at IS NULL AND id NOT IN (
            SELECT MAX(id) FROM exercise_sessions
            WHERE finished_at IS NULL GROUP BY user_id
        )
        """
    )
    op.execute(
        """
        DELETE FROM exercise_questions
        WHERE answered_at IS NULL AND session_id IN (
            SELECT id FROM exercise_sessions WHERE finished_at IS NOT NULL
        )
        """
    )
    op.create_index(
        "uq_exercise_sessions_user_id_open",
        "exercise_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("finished_at IS NULL"),
        sqlite_where=sa.text("finished_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_exercise_sessions_user_id_open",
        table_name="exercise_sessions",
        postgresql_where=sa.text("finished_at IS NULL"),
        sqlite_where=sa.text("finished_at IS NULL"),
    )
