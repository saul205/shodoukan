"""Create exercises

Saved exercise definitions: settings as JSON, and the collections each one
draws from in one link table per kind (entry or kanji collections).

Revision ID: 8ef13443cd30
Revises: cc326135e923
Create Date: 2026-10-04 14:42:18.110005+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8ef13443cd30"
down_revision: str | Sequence[str] | None = "cc326135e923"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("item_kind", sa.String(length=8), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "item_kind IN ('entries', 'kanji')", name=op.f("ck_exercises_item_kind")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_exercises_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exercises")),
    )
    op.create_index(
        op.f("ix_exercises_user_id"), "exercises", ["user_id"], unique=False
    )
    op.create_table(
        "exercise_entry_collections",
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["entry_collections.id"],
            name=op.f("fk_exercise_entry_collections_collection_id_entry_collections"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_exercise_entry_collections_exercise_id_exercises"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "exercise_id", "collection_id", name=op.f("pk_exercise_entry_collections")
        ),
    )
    op.create_index(
        op.f("ix_exercise_entry_collections_collection_id"),
        "exercise_entry_collections",
        ["collection_id"],
        unique=False,
    )
    op.create_table(
        "exercise_kanji_collections",
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["kanji_collections.id"],
            name=op.f("fk_exercise_kanji_collections_collection_id_kanji_collections"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_exercise_kanji_collections_exercise_id_exercises"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "exercise_id", "collection_id", name=op.f("pk_exercise_kanji_collections")
        ),
    )
    op.create_index(
        op.f("ix_exercise_kanji_collections_collection_id"),
        "exercise_kanji_collections",
        ["collection_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_exercise_kanji_collections_collection_id"),
        table_name="exercise_kanji_collections",
    )
    op.drop_table("exercise_kanji_collections")
    op.drop_index(
        op.f("ix_exercise_entry_collections_collection_id"),
        table_name="exercise_entry_collections",
    )
    op.drop_table("exercise_entry_collections")
    op.drop_index(op.f("ix_exercises_user_id"), table_name="exercises")
    op.drop_table("exercises")
