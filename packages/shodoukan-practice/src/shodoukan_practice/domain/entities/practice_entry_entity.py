"""Frozen snapshot of a shodoukan Entry, plus the mutable practice state
(enabled/disabled, added items, notes) layered on top.

The dictionary's data is never edited or removed: the user disables what
they don't want, and adds, edits and removes senses and meanings of their
own.
"""

from collections.abc import Iterable
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from ..exceptions import EntityNotFoundError, OriginalDataError
from .nested_item_lookup import Toggleable, clean_meaning, find_item
from .notes_value import Notes, parse_notes
from .timestamped_entity import TimestampedEntity

# The parts of an entry the user can enable or disable, one item at a time.
EntryPart = Literal["kanji_readings", "readings", "senses", "glosses", "examples"]
Origin = Literal["imported", "added"]


class PracticeGloss(BaseModel):
    id: int | None
    text: str
    lang: str
    type: str | None
    enabled: bool = True
    origin: Origin = "imported"


class PracticeExampleSentence(BaseModel):
    lang: str
    text: str


class PracticeExample(BaseModel):
    id: int | None
    text: str
    sentences: list[PracticeExampleSentence]
    enabled: bool = True
    origin: Origin = "imported"


class PracticeSense(BaseModel):
    id: int | None
    pos: list[str]
    misc: list[str]
    dialects: list[str]
    info: list[str]
    glosses: list[PracticeGloss]
    examples: list[PracticeExample]
    notes: Notes = None
    # A disabled sense hides its glosses and examples without changing their
    # own flags, so enabling it again brings it back as it was.
    enabled: bool = True
    origin: Origin = "imported"


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

    def set_notes(self, notes: str | None) -> None:
        notes = parse_notes(notes)
        if notes != self.notes:
            self.notes = notes
            self.touch()

    def set_sense_notes(self, sense_id: int, notes: str | None) -> None:
        sense = self._sense(sense_id)
        notes = parse_notes(notes)
        if notes != sense.notes:
            sense.notes = notes
            self.touch()

    def set_enabled(self, part: EntryPart, item_id: int, enabled: bool) -> None:
        """Show or hide one reading, spelling, sense, meaning or example."""
        item = find_item(self._items(part), item_id, part)
        if item.enabled != enabled:
            item.enabled = enabled
            self.touch()

    def add_sense(self, text: str, lang: str) -> PracticeSense:
        """Add a sense of the user's own at the end, with its first meaning.

        A sense always starts with a meaning, so it never shows up empty.
        `lang` follows the stored glosses (ISO 639-2). The new sense and its
        gloss have no id until the entry is stored.
        """
        gloss = PracticeGloss(
            id=None, text=clean_meaning(text), lang=lang, type=None, origin="added"
        )
        sense = PracticeSense(
            id=None,
            pos=[],
            misc=[],
            dialects=[],
            info=[],
            glosses=[gloss],
            examples=[],
            origin="added",
        )
        self.senses.append(sense)
        self.touch()
        return sense

    def remove_sense(self, sense_id: int) -> None:
        """Remove one of the user's own senses, with its meanings and examples."""
        sense = self._sense(sense_id)
        if sense.origin == "imported":
            raise OriginalDataError("dictionary senses can only be disabled")
        self.senses.remove(sense)
        self.touch()

    def add_gloss(self, sense_id: int, text: str, lang: str) -> PracticeGloss:
        """Add a meaning of the user's own at the end of the sense.

        `lang` follows the stored glosses (ISO 639-2, e.g. "eng"). The new
        gloss has no id until the entry is stored.
        """
        gloss = PracticeGloss(
            id=None, text=clean_meaning(text), lang=lang, type=None, origin="added"
        )
        self._sense(sense_id).glosses.append(gloss)
        self.touch()
        return gloss

    def edit_gloss(self, gloss_id: int, text: str) -> None:
        """Change the text of one of the user's own meanings."""
        _, gloss = self._own_gloss(gloss_id)
        text = clean_meaning(text)
        if text != gloss.text:
            gloss.text = text
            self.touch()

    def remove_gloss(self, gloss_id: int) -> None:
        """Remove one of the user's own meanings."""
        sense, gloss = self._own_gloss(gloss_id)
        sense.glosses.remove(gloss)
        self.touch()

    def _sense(self, sense_id: int) -> PracticeSense:
        return find_item(self.senses, sense_id, "sense")

    def _own_gloss(self, gloss_id: int) -> tuple[PracticeSense, PracticeGloss]:
        for sense in self.senses:
            for gloss in sense.glosses:
                if gloss.id == gloss_id:
                    if gloss.origin == "imported":
                        raise OriginalDataError(
                            "dictionary meanings can only be disabled"
                        )
                    return sense, gloss
        raise EntityNotFoundError(f"gloss {gloss_id} not found")

    def _items(self, part: EntryPart) -> Iterable[Toggleable]:
        if part == "kanji_readings":
            return self.kanji_readings
        if part == "readings":
            return self.readings
        if part == "senses":
            return self.senses
        if part == "glosses":
            return [g for s in self.senses for g in s.glosses]
        return [e for s in self.senses for e in s.examples]
