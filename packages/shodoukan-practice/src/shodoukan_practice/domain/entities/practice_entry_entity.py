"""Frozen snapshot of a shodoukan Entry, plus the mutable practice state
(enabled/disabled, added items) layered on top.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from .notes_value import Notes
from .timestamped_entity import TimestampedEntity


class PracticeGloss(BaseModel):
    id: int | None
    text: str
    lang: str
    type: str | None
    enabled: bool = True
    origin: Literal["imported", "added"] = "imported"


class PracticeExampleSentence(BaseModel):
    lang: str
    text: str


class PracticeExample(BaseModel):
    id: int | None
    text: str
    sentences: list[PracticeExampleSentence]
    enabled: bool = True
    origin: Literal["imported", "added"] = "imported"


class PracticeSense(BaseModel):
    id: int | None
    pos: list[str]
    misc: list[str]
    dialects: list[str]
    info: list[str]
    glosses: list[PracticeGloss]
    examples: list[PracticeExample]
    notes: Notes = None


class PracticeReading(BaseModel):
    id: int | None
    text: str
    no_kanji: bool
    info: list[str]
    restricted_to: list[str]
    enabled: bool = True


class PracticeKanjiReading(BaseModel):
    """Kanji spelling of a word entry (e.g. "食べる").

    Not to be confused with the on/kun readings of a character — see
    `PracticeReadingItem` in `practice_kanji_entity.py`.
    """

    id: int | None
    kanji: str
    info: list[str]
    enabled: bool = True


class PracticeEntry(TimestampedEntity):
    id: int | None
    user_id: UUID
    source_entry_id: int  # sole reference back to shodoukan's Entry.id
    kanji_readings: list[PracticeKanjiReading]
    readings: list[PracticeReading]
    senses: list[PracticeSense]
    jlpt: int | None
    is_common: bool
    is_active: bool = True
    notes: Notes = None

    def activate(self) -> None:
        if not self.is_active:
            self.is_active = True
            self.touch()

    def deactivate(self) -> None:
        if self.is_active:
            self.is_active = False
            self.touch()
