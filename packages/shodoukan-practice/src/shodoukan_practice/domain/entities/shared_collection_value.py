"""The portable form of a collection: what an exported (later, a public)
collection carries for each item, and what importing it copies.

An item travels as its dictionary reference plus the user's own data: every
part, in order, with its origin, enabled flag and text. On import the
dictionary snapshot is taken again; its imported parts are only located (by
place among the imported parts of the same list, checked by text), while
added parts are copied. `PracticeEntry` / `PracticeKanji` build these
(`to_shared`) and apply them (`merge_shared`).

Each part carries three ids from the exporter's database:

- `id`: the exporter's row; the copy records it as `source_id`.
- `original_id`: the part every copy of it shares, its identity.
- `edited_id` (parts with content: spellings, readings, meanings, examples):
  the version of that content, the row where it was last written. A copy
  keeps it until its owner edits it.

An added part is skipped when the item already has that version; another
version of the same part is added next to it (better to duplicate than to
lose it). Senses and words are containers: they're matched by identity, and
their parts merged. None of these ids is stored as an id by the importer.
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
    id: int | None = None
    original_id: int | None = None
    enabled: bool = True

    @property
    def identity(self) -> int | None:
        """The part all its copies share (a hand-written file may omit it)."""
        return self.original_id if self.original_id is not None else self.id


class SharedContent(SharedPart):
    """A part with content of its own, which has versions."""

    edited_id: int | None = None

    @property
    def version(self) -> int | None:
        return self.edited_id if self.edited_id is not None else self.id


class SharedSpelling(SharedContent):
    text: str

    @model_validator(mode="after")
    def _check_added(self) -> Self:
        if self.origin == "added":
            clean_spelling(self.text)
        return self


class SharedReading(SharedContent):
    text: str

    @model_validator(mode="after")
    def _check_added(self) -> Self:
        if self.origin == "added":
            clean_kana(self.text)
        return self


class SharedMeaning(SharedContent):
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


class SharedExample(SharedContent):
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
    original_id: int | None = None
    source_entry_id: int | None
    is_active: bool = True
    notes: Notes = None
    spellings: list[SharedSpelling] = Field(default=[], max_length=MAX_SHARED_PARTS)
    readings: list[SharedReading] = Field(default=[], max_length=MAX_SHARED_PARTS)
    senses: list[SharedSense] = Field(default=[], max_length=MAX_SHARED_PARTS)

    @property
    def identity(self) -> int | None:
        """For a word of the owner's own: the word all its copies share."""
        return self.original_id if self.original_id is not None else self.id

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
