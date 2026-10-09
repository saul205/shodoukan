"""The portable form of a collection: what an exported (later, a public)
collection carries for each item, and what importing it copies.

An item travels as its dictionary reference plus the user's own data: every
part, in order, with its origin, enabled flag and text. On import the
dictionary snapshot is taken again; its imported parts are only located (by
place among the imported parts of the same list, checked by text), while
added parts are copied, with their ids as provenance so a re-import doesn't
duplicate them. `PracticeEntry` / `PracticeKanji` build these (`to_shared`)
and apply them (`merge_shared`).

Ids are the origin's, never the importer's: they're only compared, never
stored as ids.
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .nested_item_lookup import (
    clean_kana,
    clean_meaning,
    clean_sentence,
    clean_spelling,
)
from .notes_value import Notes

SharedOrigin = Literal["imported", "added"]

# Bounds a file can't exceed, so a crafted one can't blow up an import.
MAX_SHARED_ITEMS = 5000
MAX_SHARED_PARTS = 500


class SharedValue(BaseModel):
    model_config = ConfigDict(frozen=True)


class SharedPart(SharedValue):
    """A part of an item: what it is, where it came from, whether it's shown."""

    origin: SharedOrigin
    # The origin's id for the part, and the id it was copied from in turn.
    id: int | None = None
    copied_from_id: int | None = None
    enabled: bool = True

    @property
    def provenance(self) -> set[int]:
        """The ids that identify this part across copies."""
        return {i for i in (self.id, self.copied_from_id) if i is not None}


class SharedSpelling(SharedPart):
    text: str

    @model_validator(mode="after")
    def _check_added(self) -> Self:
        if self.origin == "added":
            clean_spelling(self.text)
        return self


class SharedReading(SharedPart):
    text: str

    @model_validator(mode="after")
    def _check_added(self) -> Self:
        if self.origin == "added":
            clean_kana(self.text)
        return self


class SharedMeaning(SharedPart):
    """An entry gloss (ISO 639-2 `lang`) or a kanji meaning (ISO 639-1)."""

    text: str
    lang: str = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def _check_added(self) -> Self:
        if self.origin == "added":
            clean_meaning(self.text)
        return self


class SharedSentence(SharedValue):
    lang: str = Field(min_length=1, max_length=8)
    text: str


class SharedExample(SharedPart):
    """An example sentence: the Japanese one (`jpn`) and its translations."""

    sentences: list[SharedSentence] = Field(default=[], max_length=MAX_SHARED_PARTS)

    @model_validator(mode="after")
    def _check_added(self) -> Self:
        if self.origin == "added":
            if not any(s.lang == "jpn" for s in self.sentences):
                raise ValueError("an example needs its Japanese sentence")
            for sentence in self.sentences:
                clean_sentence(sentence.text)
        return self


class SharedSense(SharedPart):
    notes: Notes = None
    glosses: list[SharedMeaning] = Field(default=[], max_length=MAX_SHARED_PARTS)
    examples: list[SharedExample] = Field(default=[], max_length=MAX_SHARED_PARTS)

    @model_validator(mode="after")
    def _check_added(self) -> Self:
        if self.origin == "added":
            if any(g.origin == "imported" for g in self.glosses) or any(
                e.origin == "imported" for e in self.examples
            ):
                raise ValueError("a sense of the user's own has no dictionary parts")
            if not self.glosses:
                raise ValueError("a sense of the user's own needs a meaning")
            if len({g.lang for g in self.glosses}) > 1:
                raise ValueError("a sense's meanings are all in one language")
        return self


class SharedEntry(SharedValue):
    """A word: its dictionary entry (`source_entry_id`), or a word of the
    owner's own (`None`), which travels whole."""

    id: int | None = None
    copied_from_id: int | None = None
    source_entry_id: int | None
    is_active: bool = True
    notes: Notes = None
    spellings: list[SharedSpelling] = Field(default=[], max_length=MAX_SHARED_PARTS)
    readings: list[SharedReading] = Field(default=[], max_length=MAX_SHARED_PARTS)
    senses: list[SharedSense] = Field(default=[], max_length=MAX_SHARED_PARTS)

    @property
    def provenance(self) -> set[int]:
        return {i for i in (self.id, self.copied_from_id) if i is not None}

    @model_validator(mode="after")
    def _check_own(self) -> Self:
        if self.source_entry_id is None:
            parts: list[SharedPart] = [*self.spellings, *self.readings, *self.senses]
            if any(p.origin == "imported" for p in parts):
                raise ValueError("a word of the user's own has no dictionary parts")
            if not self.readings:
                raise ValueError("a word needs a reading")
        return self


class SharedKanjiReading(SharedValue):
    """An on/kun reading or nanori: always the dictionary's, only its flag
    travels (checked against its text)."""

    text: str
    enabled: bool = True


class SharedKanji(SharedValue):
    id: int | None = None
    literal: str = Field(min_length=1, max_length=8)
    is_active: bool = True
    notes: Notes = None
    on_readings: list[SharedKanjiReading] = Field(
        default=[], max_length=MAX_SHARED_PARTS
    )
    kun_readings: list[SharedKanjiReading] = Field(
        default=[], max_length=MAX_SHARED_PARTS
    )
    nanori: list[SharedKanjiReading] = Field(default=[], max_length=MAX_SHARED_PARTS)
    meanings: list[SharedMeaning] = Field(default=[], max_length=MAX_SHARED_PARTS)


class SharedCollection(SharedValue):
    """A collection's name, description and items, in the order they were added.

    `name` isn't bounded like a collection's: the import fits it.
    """

    id: int | None = None
    name: str = Field(min_length=1)
    description: str | None = None


class SharedEntryCollection(SharedCollection):
    items: list[SharedEntry] = Field(default=[], max_length=MAX_SHARED_ITEMS)


class SharedKanjiCollection(SharedCollection):
    items: list[SharedKanji] = Field(default=[], max_length=MAX_SHARED_ITEMS)
