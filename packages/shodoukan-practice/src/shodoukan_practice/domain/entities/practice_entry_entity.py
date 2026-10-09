"""Frozen snapshot of a shodoukan Entry, plus the mutable practice state
(enabled/disabled, added items, notes) layered on top.

The dictionary's data is never edited or removed: the user disables what
they don't want, and adds, edits and removes senses and meanings of their
own.
"""

from collections.abc import Iterable, Sequence
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel

from ..exceptions import (
    EntityNotFoundError,
    LastMeaningError,
    LastReadingError,
    OriginalDataError,
    SenseLanguageError,
)
from .nested_item_lookup import (
    Toggleable,
    clean_kana,
    clean_meaning,
    clean_sentence,
    clean_spelling,
    find_item,
)
from .notes_value import Notes, parse_notes
from .timestamped_entity import TimestampedEntity

# The parts of an entry the user can enable or disable, one item at a time.
EntryPart = Literal["kanji_readings", "readings", "senses", "glosses", "examples"]
Origin = Literal["imported", "added"]

# Example sentences store the Japanese one under this language, like JMDict.
JAPANESE = "jpn"


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
    # JMDict's form of the word in the sentence; empty in the user's own.
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
    origin: Origin = "imported"


class PracticeKanjiReading(BaseModel):
    """Kanji spelling of a word entry (e.g. "食べる").

    Not to be confused with the on/kun readings of a character — see
    `PracticeReadingItem` in `practice_kanji_entity.py`.
    """

    id: int | None
    kanji: str
    info: list[str]
    enabled: bool = True
    origin: Origin = "imported"


class PracticeEntry(TimestampedEntity):
    id: int | None
    user_id: UUID
    # The sole reference back to shodoukan's Entry.id; None for a word the
    # user created themselves.
    source_entry_id: int | None
    kanji_readings: list[PracticeKanjiReading]
    readings: list[PracticeReading]
    senses: list[PracticeSense]
    jlpt: int | None
    is_common: bool
    is_active: bool = True
    notes: Notes = None

    @classmethod
    def create_own(
        cls,
        user_id: UUID,
        spellings: Sequence[str],
        readings: Sequence[str],
        meaning: str,
        lang: str,
    ) -> Self:
        """A word of the user's own, not in the dictionary.

        It needs a reading (kana) and a first meaning in `lang` (ISO 639-2);
        spellings are optional (a kana-only word has none). Everything in it
        is the user's (`origin="added"`). Repeated texts are kept once.
        """
        cleaned_readings = list(dict.fromkeys(clean_kana(r) for r in readings))
        if not cleaned_readings:
            raise ValueError("a word needs a reading")
        return cls(
            id=None,
            user_id=user_id,
            source_entry_id=None,
            kanji_readings=[
                _own_spelling(s) for s in dict.fromkeys(map(clean_spelling, spellings))
            ],
            readings=[_own_reading(r) for r in cleaned_readings],
            senses=[_own_sense(meaning, lang)],
            jlpt=None,
            is_common=False,
        )

    @property
    def is_own(self) -> bool:
        """Created by the user rather than imported from the dictionary."""
        return self.source_entry_id is None

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
        sense = _own_sense(text, lang)
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

    def add_spelling(self, kanji: str) -> PracticeKanjiReading:
        """Add a written form of the user's own at the end (no id until stored)."""
        spelling = _own_spelling(clean_spelling(kanji))
        self.kanji_readings.append(spelling)
        self.touch()
        return spelling

    def remove_spelling(self, spelling_id: int) -> None:
        """Remove one of the user's own written forms."""
        spelling = find_item(self.kanji_readings, spelling_id, "spelling")
        if spelling.origin == "imported":
            raise OriginalDataError("dictionary spellings can only be disabled")
        self.kanji_readings.remove(spelling)
        self.touch()

    def add_reading(self, text: str) -> PracticeReading:
        """Add a reading (kana) of the user's own at the end (no id until stored)."""
        reading = _own_reading(clean_kana(text))
        self.readings.append(reading)
        self.touch()
        return reading

    def remove_reading(self, reading_id: int) -> None:
        """Remove one of the user's own readings; a word keeps at least one."""
        reading = find_item(self.readings, reading_id, "reading")
        if reading.origin == "imported":
            raise OriginalDataError("dictionary readings can only be disabled")
        if len(self.readings) == 1:
            raise LastReadingError("a word keeps at least one reading")
        self.readings.remove(reading)
        self.touch()

    def add_gloss(self, sense_id: int, text: str, lang: str) -> PracticeGloss:
        """Add a meaning of the user's own at the end of the sense.

        `lang` follows the stored glosses (ISO 639-2, e.g. "eng"), and must be
        the sense's: a sense's meanings are all in one language
        (`SenseLanguageError`). The new gloss has no id until the entry is
        stored.
        """
        sense = self._sense(sense_id)
        if any(g.lang != lang for g in sense.glosses):
            raise SenseLanguageError(f"this sense's meanings aren't in {lang!r}")
        gloss = PracticeGloss(
            id=None, text=clean_meaning(text), lang=lang, type=None, origin="added"
        )
        sense.glosses.append(gloss)
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
        """Remove one of the user's own meanings.

        A sense keeps at least one (`LastMeaningError`): without one it would
        show in no language, nor could its examples and note be reached. To
        get rid of an own sense, remove the sense.
        """
        sense, gloss = self._own_gloss(gloss_id)
        if len(sense.glosses) == 1:
            raise LastMeaningError("a sense keeps at least one meaning")
        sense.glosses.remove(gloss)
        self.touch()

    def add_example(
        self, sense_id: int, japanese: str, translation: str | None, lang: str
    ) -> PracticeExample:
        """Add an example sentence of the user's own at the end of the sense.

        `translation` (optional) is in `lang` (ISO 639-2, e.g. "eng"). The new
        example has no id until the entry is stored.
        """
        example = PracticeExample(
            id=None,
            text="",
            sentences=_sentences([], japanese, translation, lang),
            origin="added",
        )
        self._sense(sense_id).examples.append(example)
        self.touch()
        return example

    def edit_example(
        self, example_id: int, japanese: str, translation: str | None, lang: str
    ) -> None:
        """Rewrite one of the user's own examples.

        The Japanese sentence and the translation in `lang` are replaced (no
        translation removes it); translations in other languages are kept.
        """
        _, example = self._own_example(example_id)
        sentences = _sentences(example.sentences, japanese, translation, lang)
        if sentences != example.sentences:
            example.sentences = sentences
            self.touch()

    def remove_example(self, example_id: int) -> None:
        """Remove one of the user's own examples."""
        sense, example = self._own_example(example_id)
        sense.examples.remove(example)
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

    def _own_example(self, example_id: int) -> tuple[PracticeSense, PracticeExample]:
        for sense in self.senses:
            for example in sense.examples:
                if example.id == example_id:
                    if example.origin == "imported":
                        raise OriginalDataError(
                            "dictionary examples can only be disabled"
                        )
                    return sense, example
        raise EntityNotFoundError(f"example {example_id} not found")

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


def _sentences(
    current: list[PracticeExampleSentence],
    japanese: str,
    translation: str | None,
    lang: str,
) -> list[PracticeExampleSentence]:
    """The Japanese sentence, then the translation in `lang` (none when
    blank), then the other translations already there, in their order."""
    if lang == JAPANESE:
        raise ValueError("a translation can't be in Japanese")
    sentences = [PracticeExampleSentence(lang=JAPANESE, text=clean_sentence(japanese))]
    for sentence in current:
        if sentence.lang not in (JAPANESE, lang):
            sentences.append(sentence)
    translation = (translation or "").strip()
    if translation:
        sentences.insert(1, PracticeExampleSentence(lang=lang, text=translation))
    return sentences


def _own_spelling(kanji: str) -> PracticeKanjiReading:
    return PracticeKanjiReading(id=None, kanji=kanji, info=[], origin="added")


def _own_reading(text: str) -> PracticeReading:
    return PracticeReading(
        id=None, text=text, no_kanji=False, info=[], restricted_to=[], origin="added"
    )


def _own_sense(text: str, lang: str) -> PracticeSense:
    """A sense of the user's own with its first meaning, in `lang` (ISO 639-2)."""
    gloss = PracticeGloss(
        id=None, text=clean_meaning(text), lang=lang, type=None, origin="added"
    )
    return PracticeSense(
        id=None,
        pos=[],
        misc=[],
        dialects=[],
        info=[],
        glosses=[gloss],
        examples=[],
        origin="added",
    )
