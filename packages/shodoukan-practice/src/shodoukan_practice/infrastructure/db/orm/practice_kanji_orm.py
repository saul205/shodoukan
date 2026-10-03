"""A user's imported kanji and its nested snapshot, one table per level.

On-readings, kun-readings and nanori share one table, told apart by `kind`.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from .base_orm import (
    ORIGINS,
    Base,
    children,
    created_at_column,
    in_check,
    updated_at_column,
)

READING_KINDS = ("on", "kun", "nanori")


class PracticeKanjiORM(Base):
    __tablename__ = "practice_kanji"
    __table_args__ = (UniqueConstraint("user_id", "literal"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    literal: Mapped[str] = mapped_column(String(8))
    grade: Mapped[int | None]
    stroke_count: Mapped[int]
    freq: Mapped[int | None]
    jlpt: Mapped[int | None]
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    created_at: Mapped[datetime.datetime] = created_at_column()
    updated_at: Mapped[datetime.datetime] = updated_at_column()

    reading_items: Mapped[list[PracticeKanjiReadingItemORM]] = children(
        "PracticeKanjiReadingItemORM.position"
    )
    meanings: Mapped[list[PracticeKanjiMeaningORM]] = children(
        "PracticeKanjiMeaningORM.position"
    )


class PracticeKanjiReadingItemORM(Base):
    __tablename__ = "practice_kanji_reading_items"
    __table_args__ = (CheckConstraint(in_check("kind", READING_KINDS), name="kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kanji_id: Mapped[int] = mapped_column(
        ForeignKey("practice_kanji.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(8))
    position: Mapped[int]
    text: Mapped[str]
    enabled: Mapped[bool] = mapped_column(default=True, server_default=true())


class PracticeKanjiMeaningORM(Base):
    __tablename__ = "practice_kanji_meanings"
    __table_args__ = (CheckConstraint(in_check("origin", ORIGINS), name="origin"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kanji_id: Mapped[int] = mapped_column(
        ForeignKey("practice_kanji.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    text: Mapped[str]
    lang: Mapped[str] = mapped_column(String(8))
    enabled: Mapped[bool] = mapped_column(default=True, server_default=true())
    origin: Mapped[str] = mapped_column(
        String(16), default="imported", server_default="imported"
    )
