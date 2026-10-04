"""Create exercise sessions

Runs of an exercise and their questions, the statistics store. Questions
keep a JSON snapshot of the card and point at their item through entry_id or
kanji_id, set to NULL when the item leaves the library.

Revision ID: 08d07b56c263
Revises: 8ef13443cd30
Create Date: 2026-10-04 17:06:16.326781+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "08d07b56c263"
down_revision: str | Sequence[str] | None = "8ef13443cd30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exercise_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=True),
        sa.Column("exercise_name", sa.String(length=100), nullable=False),
        sa.Column("item_kind", sa.String(length=8), nullable=False),
        sa.Column("meaning_lang", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "item_kind IN ('entries', 'kanji')",
            name=op.f("ck_exercise_sessions_item_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_exercise_sessions_exercise_id_exercises"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_exercise_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exercise_sessions")),
    )
    op.create_index(
        op.f("ix_exercise_sessions_exercise_id"),
        "exercise_sessions",
        ["exercise_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exercise_sessions_user_id"),
        "exercise_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "exercise_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=True),
        sa.Column("kanji_id", sa.Integer(), nullable=True),
        sa.Column("prompt_fields", sa.JSON(), nullable=False),
        sa.Column("answer_field", sa.String(length=16), nullable=False),
        sa.Column("prompt", sa.JSON(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("correct_option", sa.Integer(), nullable=False),
        sa.Column("back", sa.JSON(), nullable=False),
        sa.Column("answer", sa.JSON(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "entry_id IS NULL OR kanji_id IS NULL",
            name=op.f("ck_exercise_questions_one_item"),
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["practice_entries.id"],
            name=op.f("fk_exercise_questions_entry_id_practice_entries"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["kanji_id"],
            ["practice_kanji.id"],
            name=op.f("fk_exercise_questions_kanji_id_practice_kanji"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["exercise_sessions.id"],
            name=op.f("fk_exercise_questions_session_id_exercise_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exercise_questions")),
    )
    op.create_index(
        op.f("ix_exercise_questions_entry_id"),
        "exercise_questions",
        ["entry_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exercise_questions_kanji_id"),
        "exercise_questions",
        ["kanji_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exercise_questions_session_id"),
        "exercise_questions",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_exercise_questions_session_id"), table_name="exercise_questions"
    )
    op.drop_index(
        op.f("ix_exercise_questions_kanji_id"), table_name="exercise_questions"
    )
    op.drop_index(
        op.f("ix_exercise_questions_entry_id"), table_name="exercise_questions"
    )
    op.drop_table("exercise_questions")
    op.drop_index(op.f("ix_exercise_sessions_user_id"), table_name="exercise_sessions")
    op.drop_index(
        op.f("ix_exercise_sessions_exercise_id"), table_name="exercise_sessions"
    )
    op.drop_table("exercise_sessions")
