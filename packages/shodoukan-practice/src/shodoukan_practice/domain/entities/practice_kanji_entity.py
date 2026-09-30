"""Frozen snapshot of a shodoukan Kanji, plus the mutable practice state
(enabled/disabled, added items) layered on top.
"""

from typing import Literal

from pydantic import BaseModel

from .timestamped_entity import TimestampedEntity


class PracticeReadingItem(BaseModel):
    """A single on-reading, kun-reading or nanori.

    Gets its own local identity because shodoukan doesn't expose one (they
    are plain string lists there).
    """

    id: int | None
    text: str
    enabled: bool = True


class PracticeKanjiMeaning(BaseModel):
    id: int | None
    text: str
    lang: str
    enabled: bool = True
    origin: Literal["imported", "added"] = "imported"


class PracticeKanji(TimestampedEntity):
    id: int | None
    user_id: int
    literal: str  # sole reference: shodoukan's Kanji.literal
    grade: int | None
    stroke_count: int
    freq: int | None
    jlpt: int | None
    on_readings: list[PracticeReadingItem]
    kun_readings: list[PracticeReadingItem]
    nanori: list[PracticeReadingItem]
    meanings: list[PracticeKanjiMeaning]
    is_active: bool = True

    def activate(self) -> None:
        if not self.is_active:
            self.is_active = True
            self.touch()

    def deactivate(self) -> None:
        if self.is_active:
            self.is_active = False
            self.touch()
