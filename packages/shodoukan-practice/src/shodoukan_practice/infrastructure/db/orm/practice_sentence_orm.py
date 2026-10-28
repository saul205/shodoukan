"""A sentence of the user's library, its translations and its words.

A word points at the library word and sense it's linked to; removing either
from the library leaves the word unlinked (`SET NULL`), so the sentence and
its gap stay.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from .base_orm import (
    ORIGINS,
    Base,
    children,
    created_at_column,
    in_check,
    updated_at_column,
)


class PracticeSentenceORM(Base):
    __tablename__ = "practice_sentences"
    __table_args__ = (CheckConstraint(in_check("origin", ORIGINS), name="origin"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    notes: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(
        String(16), default="imported", server_default="imported"
    )
    original_id: Mapped[int | None]
    source_id: Mapped[int | None]
    edited_id: Mapped[int | None]
    revision: Mapped[int] = mapped_column(default=0, server_default="0")
    # What brings the sentence (a copy): collection ids, or "file", as JSON.
    source_collection_ids: Mapped[list[int | str]] = mapped_column(
        JSON, default=list, server_default="[]"
    )
    created_at: Mapped[datetime.datetime] = created_at_column()
    updated_at: Mapped[datetime.datetime] = updated_at_column()

    translations: Mapped[list[PracticeSentenceTranslationORM]] = children(
        "PracticeSentenceTranslationORM.position"
    )
    words: Mapped[list[PracticeSentenceWordORM]] = children(
        "PracticeSentenceWordORM.position"
    )


class PracticeSentenceTranslationORM(Base):
    """A translation of a sentence; no identity in the domain, only a row id."""

    __tablename__ = "practice_sentence_translations"

    id: Mapped[int] = mapped_column(primary_key=True)
    sentence_id: Mapped[int] = mapped_column(
        ForeignKey("practice_sentences.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    lang: Mapped[str] = mapped_column(String(8))
    text: Mapped[str] = mapped_column(Text)


class PracticeSentenceWordORM(Base):
    __tablename__ = "practice_sentence_words"
    __table_args__ = (
        CheckConstraint(
            "(span_start IS NULL) = (span_end IS NULL)", name="span_complete"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sentence_id: Mapped[int] = mapped_column(
        ForeignKey("practice_sentences.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    span_start: Mapped[int | None]
    span_end: Mapped[int | None]
    lemma: Mapped[str | None]
    reading: Mapped[str | None]
    pos: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    # `Inflection`: endings as a JSON list and the form; NULL endings means
    # not analyzed (an analyzed noun has `[]`).
    inflection_endings: Mapped[list[str] | None] = mapped_column(JSON)
    inflection_form: Mapped[str | None] = mapped_column(String(32))
    entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("practice_entries.id", ondelete="SET NULL"), index=True
    )
    sense_id: Mapped[int | None] = mapped_column(
        ForeignKey("practice_senses.id", ondelete="SET NULL")
    )
