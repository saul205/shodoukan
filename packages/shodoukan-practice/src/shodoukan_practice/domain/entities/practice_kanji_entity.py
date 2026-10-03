"""Frozen snapshot of a shodoukan Kanji, plus the mutable practice state
(enabled/disabled, added meanings, notes) layered on top.

The dictionary's data is never edited or removed: the user disables what
they don't want, and adds, edits and removes meanings of their own.
"""

from collections.abc import Iterable
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from ..exceptions import OriginalDataError
from .nested_item_lookup import Toggleable, clean_meaning, find_item
from .notes_value import Notes, parse_notes
from .timestamped_entity import TimestampedEntity

# The parts of a kanji the user can enable or disable, one item at a time.
# "readings" covers on, kun and nanori: their ids share one table.
KanjiPart = Literal["readings", "meanings"]


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
    user_id: UUID
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
    notes: Notes = None

    def activate(self) -> None:
        if not self.is_active:
            self.is_active = True
            self.touch()

    def deactivate(self) -> None:
        if self.is_active:
            self.is_active = False
            self.touch()

    def set_notes(self, notes: str | None) -> None:
        notes = parse_notes(notes)
        if notes != self.notes:
            self.notes = notes
            self.touch()

    def set_enabled(self, part: KanjiPart, item_id: int, enabled: bool) -> None:
        """Show or hide one reading or meaning."""
        item = find_item(self._items(part), item_id, part)
        if item.enabled != enabled:
            item.enabled = enabled
            self.touch()

    def add_meaning(self, text: str, lang: str) -> PracticeKanjiMeaning:
        """Add a meaning of the user's own at the end.

        `lang` follows the stored meanings (ISO 639-1, e.g. "en"). The new
        meaning has no id until the kanji is stored.
        """
        meaning = PracticeKanjiMeaning(
            id=None, text=clean_meaning(text), lang=lang, origin="added"
        )
        self.meanings.append(meaning)
        self.touch()
        return meaning

    def edit_meaning(self, meaning_id: int, text: str) -> None:
        """Change the text of one of the user's own meanings."""
        meaning = self._own_meaning(meaning_id)
        text = clean_meaning(text)
        if text != meaning.text:
            meaning.text = text
            self.touch()

    def remove_meaning(self, meaning_id: int) -> None:
        """Remove one of the user's own meanings."""
        self.meanings.remove(self._own_meaning(meaning_id))
        self.touch()

    def _own_meaning(self, meaning_id: int) -> PracticeKanjiMeaning:
        meaning = find_item(self.meanings, meaning_id, "meaning")
        if meaning.origin == "imported":
            raise OriginalDataError("dictionary meanings can only be disabled")
        return meaning

    def _items(self, part: KanjiPart) -> Iterable[Toggleable]:
        if part == "meanings":
            return self.meanings
        return [*self.on_readings, *self.kun_readings, *self.nanori]
