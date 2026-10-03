"""A user's imported entry and its nested snapshot, one table per level.

Every nested item has its own row (and id) so enabling, disabling or adding
one is a single-row write. `position` keeps the original order.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from .base_orm import (
    ORIGINS,
    Base,
    children,
    created_at_column,
    in_check,
    updated_at_column,
)


class PracticeEntryORM(Base):
    __tablename__ = "practice_entries"
    __table_args__ = (UniqueConstraint("user_id", "source_entry_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source_entry_id: Mapped[int]
    jlpt: Mapped[int | None]
    is_common: Mapped[bool]
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    created_at: Mapped[datetime.datetime] = created_at_column()
    updated_at: Mapped[datetime.datetime] = updated_at_column()

    kanji_readings: Mapped[list[PracticeEntryKanjiReadingORM]] = children(
        "PracticeEntryKanjiReadingORM.position"
    )
    readings: Mapped[list[PracticeEntryReadingORM]] = children(
        "PracticeEntryReadingORM.position"
    )
    senses: Mapped[list[PracticeSenseORM]] = children("PracticeSenseORM.position")


class PracticeEntryKanjiReadingORM(Base):
    __tablename__ = "practice_entry_kanji_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("practice_entries.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    kanji: Mapped[str]
    info: Mapped[list[str]] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(default=True, server_default=true())


class PracticeEntryReadingORM(Base):
    __tablename__ = "practice_entry_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("practice_entries.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    text: Mapped[str]
    no_kanji: Mapped[bool]
    info: Mapped[list[str]] = mapped_column(JSON)
    restricted_to: Mapped[list[str]] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(default=True, server_default=true())


class PracticeSenseORM(Base):
    __tablename__ = "practice_senses"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("practice_entries.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    pos: Mapped[list[str]] = mapped_column(JSON)
    misc: Mapped[list[str]] = mapped_column(JSON)
    dialects: Mapped[list[str]] = mapped_column(JSON)
    info: Mapped[list[str]] = mapped_column(JSON)

    glosses: Mapped[list[PracticeGlossORM]] = children("PracticeGlossORM.position")
    examples: Mapped[list[PracticeExampleORM]] = children("PracticeExampleORM.position")


class PracticeGlossORM(Base):
    __tablename__ = "practice_glosses"
    __table_args__ = (CheckConstraint(in_check("origin", ORIGINS), name="origin"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sense_id: Mapped[int] = mapped_column(
        ForeignKey("practice_senses.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    text: Mapped[str]
    lang: Mapped[str] = mapped_column(String(8))
    type: Mapped[str | None]
    enabled: Mapped[bool] = mapped_column(default=True, server_default=true())
    origin: Mapped[str] = mapped_column(
        String(16), default="imported", server_default="imported"
    )


class PracticeExampleORM(Base):
    __tablename__ = "practice_examples"
    __table_args__ = (CheckConstraint(in_check("origin", ORIGINS), name="origin"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sense_id: Mapped[int] = mapped_column(
        ForeignKey("practice_senses.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    text: Mapped[str]
    enabled: Mapped[bool] = mapped_column(default=True, server_default=true())
    origin: Mapped[str] = mapped_column(
        String(16), default="imported", server_default="imported"
    )

    sentences: Mapped[list[PracticeExampleSentenceORM]] = children(
        "PracticeExampleSentenceORM.position"
    )


class PracticeExampleSentenceORM(Base):
    """A translation of an example; no identity in the domain, only a row id."""

    __tablename__ = "practice_example_sentences"

    id: Mapped[int] = mapped_column(primary_key=True)
    example_id: Mapped[int] = mapped_column(
        ForeignKey("practice_examples.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    lang: Mapped[str] = mapped_column(String(8))
    text: Mapped[str]
