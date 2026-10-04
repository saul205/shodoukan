"""Exercise sessions and their questions: the statistics store.

A question keeps its prompt, options and back as JSON (a snapshot: always
read whole), and the data statistics filter by as real columns (item,
fields, right or wrong, when, how long). The item is `entry_id` or `kanji_id`
depending on the session's `item_kind`, so each has a real foreign key; both
are set to NULL when the item leaves the library. Deleting the exercise sets
`exercise_id` to NULL: the history stays.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base_orm import (
    Base,
    UtcDateTime,
    children,
    created_at_column,
    in_check,
    updated_at_column,
)
from .exercise_orm import ITEM_KINDS


class ExerciseSessionORM(Base):
    __tablename__ = "exercise_sessions"
    __table_args__ = (
        CheckConstraint(in_check("item_kind", ITEM_KINDS), name="item_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[int | None] = mapped_column(
        ForeignKey("exercises.id", ondelete="SET NULL"), index=True
    )
    exercise_name: Mapped[str] = mapped_column(String(100))
    item_kind: Mapped[str] = mapped_column(String(8))
    meaning_lang: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime.datetime] = created_at_column()
    updated_at: Mapped[datetime.datetime] = updated_at_column()
    finished_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime)

    questions: Mapped[list[ExerciseQuestionORM]] = children(
        "ExerciseQuestionORM.position"
    )


class ExerciseQuestionORM(Base):
    __tablename__ = "exercise_questions"
    __table_args__ = (
        CheckConstraint("entry_id IS NULL OR kanji_id IS NULL", name="one_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("exercise_sessions.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("practice_entries.id", ondelete="SET NULL"), index=True
    )
    kanji_id: Mapped[int | None] = mapped_column(
        ForeignKey("practice_kanji.id", ondelete="SET NULL"), index=True
    )
    prompt_fields: Mapped[list[str]] = mapped_column(JSON)
    answer_field: Mapped[str] = mapped_column(String(16))
    prompt: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    correct_option: Mapped[int]
    back: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    # SQL NULL until answered (not a JSON null), so it can be filtered on.
    answer: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True))
    is_correct: Mapped[bool | None]
    answered_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime)
    response_ms: Mapped[int | None]
