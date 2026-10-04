"""Saved exercises and the collections they draw from.

`settings` is JSON: it depends on the exercise type and is always read and
written whole, validated by the domain model. Entry and kanji exercises share
the table (`item_kind`); their collections go in one link table per kind so
each has a real foreign key. Only the one matching `item_kind` is used.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base_orm import Base, children, created_at_column, in_check, updated_at_column

ITEM_KINDS = ("entries", "kanji")


class ExerciseORM(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint(in_check("item_kind", ITEM_KINDS), name="item_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None]
    item_kind: Mapped[str] = mapped_column(String(8))
    settings: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = created_at_column()
    updated_at: Mapped[datetime.datetime] = updated_at_column()

    entry_collections: Mapped[list[ExerciseEntryCollectionORM]] = children(
        "ExerciseEntryCollectionORM.position"
    )
    kanji_collections: Mapped[list[ExerciseKanjiCollectionORM]] = children(
        "ExerciseKanjiCollectionORM.position"
    )


class ExerciseEntryCollectionORM(Base):
    __tablename__ = "exercise_entry_collections"

    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True
    )
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("entry_collections.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,  # deleting a collection finds its links
    )
    position: Mapped[int]


class ExerciseKanjiCollectionORM(Base):
    __tablename__ = "exercise_kanji_collections"

    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True
    )
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("kanji_collections.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    position: Mapped[int]
