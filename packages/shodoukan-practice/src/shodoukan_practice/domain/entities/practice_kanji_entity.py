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
from .nested_item_lookup import (
    Toggleable,
    clean_meaning,
    find_item,
    identity,
    merge_parts,
    version,
)
from .notes_value import Notes, parse_notes
from .shared_collection_value import SharedKanji, SharedKanjiReading, SharedMeaning
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
    # Where a copy came from (see `PracticeGloss`).
    original_id: int | None = None
    source_id: int | None = None
    edited_id: int | None = None


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
            meaning.edited_id = None  # this version is now the user's
            self.touch()

    def remove_meaning(self, meaning_id: int) -> None:
        """Remove one of the user's own meanings."""
        self.meanings.remove(self._own_meaning(meaning_id))
        self.touch()

    def to_shared(self) -> SharedKanji:
        """What this kanji carries in an exported collection."""
        return SharedKanji(
            id=self.id,
            literal=self.literal,
            is_active=self.is_active,
            notes=self.notes,
            on_readings=_shared_readings(self.on_readings),
            kun_readings=_shared_readings(self.kun_readings),
            nanori=_shared_readings(self.nanori),
            meanings=[
                SharedMeaning(
                    origin=m.origin,
                    id=m.id,
                    original_id=identity(m),
                    edited_id=version(m),
                    enabled=m.enabled,
                    text=m.text,
                    lang=m.lang,
                )
                for m in self.meanings
            ],
        )

    def merge_shared(self, shared: SharedKanji, created: bool) -> bool:
        """Take what a shared copy of this kanji adds.

        Same rules as `PracticeEntry.merge_shared`: the meanings the user
        added that this kanji doesn't have yet are appended, notes are copied
        only when there are none, and the flags are taken only when the kanji
        was `created` by this import. Returns whether anything changed.
        """
        if shared.literal != self.literal:
            raise ValueError(f"{shared.literal!r} isn't {self.literal!r}")
        changed = False
        if created:
            if self.is_active != shared.is_active:
                self.is_active = shared.is_active
                changed = True
            for ours, theirs in (
                (self.on_readings, shared.on_readings),
                (self.kun_readings, shared.kun_readings),
                (self.nanori, shared.nanori),
            ):
                changed |= _take_reading_flags(ours, theirs)
        if self.notes is None and shared.notes is not None:
            self.notes = shared.notes
            changed = True
        changed |= merge_parts(
            self.meanings,
            shared.meanings,
            created=created,
            same=lambda ours, theirs: ours.text == theirs.text,
            copy=_copied_meaning,
        )
        if changed:
            self.touch()
        return changed

    def _own_meaning(self, meaning_id: int) -> PracticeKanjiMeaning:
        meaning = find_item(self.meanings, meaning_id, "meaning")
        if meaning.origin == "imported":
            raise OriginalDataError("dictionary meanings can only be disabled")
        return meaning

    def _items(self, part: KanjiPart) -> Iterable[Toggleable]:
        if part == "meanings":
            return self.meanings
        return [*self.on_readings, *self.kun_readings, *self.nanori]


def _shared_readings(items: list[PracticeReadingItem]) -> list[SharedKanjiReading]:
    return [SharedKanjiReading(text=r.text, enabled=r.enabled) for r in items]


def _take_reading_flags(
    ours: list[PracticeReadingItem], theirs: list[SharedKanjiReading]
) -> bool:
    """Take the flags of the readings that are in the same place, same text."""
    changed = False
    for item, shared in zip(ours, theirs, strict=False):
        if item.text == shared.text and item.enabled != shared.enabled:
            item.enabled = shared.enabled
            changed = True
    return changed


def _copied_meaning(part: SharedMeaning) -> PracticeKanjiMeaning:
    return PracticeKanjiMeaning(
        id=None,
        text=clean_meaning(part.text),
        lang=part.lang,
        enabled=part.enabled,
        origin="added",
        original_id=part.identity,
        source_id=part.id,
        edited_id=part.version,
    )
