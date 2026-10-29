"""A sentence of the user's library, linked to the words it uses.

Sentences are items of their own, not parts of a word: one sentence can use
several of the user's words, and a word has as many sentences as the user
gives it. The link lives in the sentence's `words`. A word with a span (where
it is in the sentence) is a gap an exercise can ask; one without a span is
linked to the word but not asked until it's marked. "The sentences of a word"
is the reverse query, by `entry_id`.

A sentence from the dictionary (JMDict, `origin="imported"`) is never edited,
only deactivated; the user's own (`"added"`) can be rewritten. The words, and
what the analyzer says about them (`lemma`, `reading`, `pos`, `inflection`),
belong to the user in both. See docs/practice/proposals/sentences.md.
"""

from collections.abc import Sequence
from itertools import pairwise
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..exceptions import OriginalDataError, SentenceWordError
from .nested_item_lookup import (
    SourceRef,
    Version,
    brought_by,
    clean_kana,
    clean_sentence,
    find_item,
    identity,
)
from .notes_value import Notes, parse_notes
from .practice_entry_entity import JAPANESE, Origin
from .timestamped_entity import TimestampedEntity


class Inflection(BaseModel):
    """The form of a word in a sentence: what follows it inside its gap, and
    the form it ends in (`domain/services/inflection_service.py`)."""

    model_config = ConfigDict(frozen=True)

    # Lemmas of the morphemes after the word: ("れる", "た") for 引かれた.
    endings: tuple[str, ...]
    # Form of the last morpheme without its variant ("終止形"); `None` when
    # it doesn't inflect (a noun alone).
    form: str | None


class SentenceTranslation(BaseModel):
    lang: str
    text: str


class SentenceWord(BaseModel):
    """A word of the sentence: where it is, what it is, and which library
    word (and sense) it's linked to."""

    id: int | None
    # Where the word is in the sentence, in characters; both or neither. No
    # span: linked, but not a gap yet.
    start: int | None = None
    end: int | None = None
    # What the analyzer says (`None` until analyzed); lemma and reading can
    # be corrected by the user.
    lemma: str | None = None
    reading: str | None = None
    pos: list[str] = Field(default_factory=list)
    inflection: Inflection | None = None
    # The library word and sense; `None` when unlinked (or the word was
    # removed from the library).
    entry_id: int | None = None
    sense_id: int | None = None

    @model_validator(mode="after")
    def _check_span(self) -> Self:
        if (self.start is None) != (self.end is None):
            raise ValueError("a word's span has a start and an end, or neither")
        if (
            self.start is not None
            and self.end is not None
            and (self.start < 0 or self.end <= self.start)
        ):
            raise ValueError("a word's span must be a non-empty range")
        return self

    @property
    def has_span(self) -> bool:
        return self.start is not None

    @property
    def is_analyzed(self) -> bool:
        return self.lemma is not None


class PracticeSentence(TimestampedEntity):
    id: int | None
    user_id: UUID
    text: str
    translations: list[SentenceTranslation] = Field(default_factory=list)
    words: list[SentenceWord] = Field(default_factory=list)
    is_active: bool = True
    notes: Notes = None
    origin: Origin = "imported"
    # Where a copy came from, as for an entry's parts (see
    # `shared_collection_value`). `None` is this row itself.
    original_id: int | None = None
    source_id: int | None = None
    edited_id: int | None = None
    revision: int = 0
    source_collection_ids: list[SourceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Self:
        _check_spans(self.text, self.words)
        if any(t.lang == JAPANESE for t in self.translations):
            raise ValueError("a translation can't be in Japanese")
        return self

    @classmethod
    def from_dictionary(
        cls,
        user_id: UUID,
        text: str,
        translations: Sequence[SentenceTranslation],
        word: str,
        entry_id: int | None,
        sense_id: int | None,
    ) -> Self:
        """A JMDict example sentence of a library word.

        `word` is the word's form in the sentence (JMDict's `text`, maybe
        inflected): its first occurrence is the gap. When it isn't found, the
        word is linked without a span.
        """
        sentence = cls(
            id=None,
            user_id=user_id,
            text=clean_sentence(text),
            translations=[t for t in translations if t.lang != JAPANESE],
        )
        sentence.add_dictionary_word(word, entry_id, sense_id)
        return sentence

    @classmethod
    def copied(
        cls,
        user_id: UUID,
        text: str,
        translations: Sequence[SentenceTranslation],
        *,
        is_active: bool,
        original_id: int | None,
        source_id: int | None,
        edited_id: int | None,
        revision: int,
        source: SourceRef | None,
    ) -> Self:
        """A copy of someone's own sentence (shared with a collection): the
        user's, remembering the sentence all copies share (`original_id`),
        the row it came from and its version, and the collection that brings
        it. Its words are added by whoever copies it."""
        return cls(
            id=None,
            user_id=user_id,
            text=clean_sentence(text),
            translations=[t for t in translations if t.lang != JAPANESE],
            is_active=is_active,
            origin="added",
            original_id=original_id,
            source_id=source_id,
            edited_id=edited_id if edited_id is not None else source_id,
            revision=revision,
            source_collection_ids=brought_by(source),
        )

    @classmethod
    def create_own(
        cls, user_id: UUID, text: str, translation: str | None, lang: str
    ) -> Self:
        """A sentence of the user's own, with an optional translation in
        `lang` (ISO 639-2, e.g. "eng") and no words yet."""
        return cls(
            id=None,
            user_id=user_id,
            text=clean_sentence(text),
            translations=_translations([], translation, lang),
            origin="added",
        )

    @property
    def is_own(self) -> bool:
        return self.origin == "added"

    @property
    def identity(self) -> int | None:
        """The sentence all copies of this one share."""
        return identity(self)

    @property
    def version(self) -> Version | None:
        """The version of its content: the row that wrote it, and its
        revision there (as for an entry's parts)."""
        row = self.edited_id if self.edited_id is not None else self.id
        return None if row is None else (row, self.revision)

    def brought_by(self, source: SourceRef) -> bool:
        """Remember one more collection that brings this copy (a sentence
        the user wrote or edited isn't anyone's to bring). Returns whether
        anything changed."""
        if self.edited_id is None or source in self.source_collection_ids:
            return False
        self.source_collection_ids = [*self.source_collection_ids, source]
        self.touch()
        return True

    def untouched_from(self, source: int) -> bool:
        """Whether that collection brings it and the user hasn't edited it."""
        return (
            self.is_own
            and source in self.source_collection_ids
            and self.edited_id is not None
        )

    def let_go(self, source: int) -> bool:
        """The collection no longer brings it. Returns whether nothing does
        any more (the copy can go)."""
        if source in self.source_collection_ids:
            self.source_collection_ids = [
                s for s in self.source_collection_ids if s != source
            ]
            self.touch()
        return not self.source_collection_ids

    def surface(self, word: SentenceWord) -> str | None:
        """The text of the word in the sentence, if it has a span."""
        if word.start is None or word.end is None:
            return None
        return self.text[word.start : word.end]

    def words_of(self, entry_id: int) -> list[SentenceWord]:
        return [w for w in self.words if w.entry_id == entry_id]

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

    def rewrite(self, text: str, translation: str | None, lang: str) -> None:
        """Rewrite one of the user's own sentences.

        The translation in `lang` is replaced (none removes it); the others
        are kept. A word keeps its span if its text is still there, at the
        same place or elsewhere; otherwise it loses its span and its analysis
        and stays linked.
        """
        if not self.is_own:
            raise OriginalDataError("dictionary sentences can only be deactivated")
        text = clean_sentence(text)
        translations = _translations(self.translations, translation, lang)
        if text == self.text and translations == self.translations:
            return
        if text != self.text:
            words = _relocated(self.words, self.text, text)
            # Each assignment is validated against the other field: assign
            # first whichever keeps every span inside the text.
            if len(text) >= len(self.text):
                self.text = text
                self.words = words
            else:
                self.words = words
                self.text = text
        self.translations = translations
        self.edited_id = None  # this version is now the user's
        self.revision += 1
        self.touch()

    def add_word(
        self,
        start: int | None,
        end: int | None,
        entry_id: int | None = None,
        sense_id: int | None = None,
        analysis: tuple[str, str, Sequence[str], Inflection | None] | None = None,
    ) -> SentenceWord:
        """Mark a word of the sentence, linked or not (no id until stored),
        with its `(lemma, reading, pos, inflection)` if known (a copy brings
        its owner's)."""
        if analysis is not None and start is None:
            raise SentenceWordError("only a word with a span can be analyzed")
        lemma, reading, pos, inflection = analysis or (None, None, (), None)
        word = SentenceWord(
            id=None,
            start=start,
            end=end,
            lemma=lemma,
            reading=reading,
            pos=list(pos),
            inflection=inflection,
            entry_id=entry_id,
            sense_id=sense_id,
        )
        self._set_words([*self.words, word])
        return word

    def add_dictionary_word(
        self, form: str, entry_id: int | None, sense_id: int | None
    ) -> SentenceWord | None:
        """Link one more library word, given its form in the sentence.

        The gap is the first occurrence of `form` no other word takes; when
        there's none, the word is linked without a span. Nothing changes (and
        `None` is returned) if the sentence already has a word linked to
        `entry_id`.
        """
        if entry_id is not None and self.words_of(entry_id):
            return None
        taken = [
            (w.start, w.end)
            for w in self.words
            if w.start is not None and w.end is not None
        ]
        start = _free_occurrence(self.text, form, taken) if form else None
        end = None if start is None else start + len(form)
        return self.add_word(start, end, entry_id=entry_id, sense_id=sense_id)

    def remove_word(self, word_id: int) -> None:
        word = self._word(word_id)
        self._set_words([w for w in self.words if w is not word])

    def mark_word(self, word_id: int, start: int, end: int) -> None:
        """Set where a word is in the sentence; a new span drops its analysis."""
        self.mark_word_at(self._position(word_id), start, end)

    def mark_word_at(self, position: int, start: int, end: int) -> None:
        """`mark_word` for the word at `position` (one not stored yet has no
        id)."""
        word = self.words[position]
        if (word.start, word.end) == (start, end):
            return
        moved = _unanalyzed(word, start, end)
        self._set_words([moved if w is word else w for w in self.words])

    def link_word(self, word_id: int, entry_id: int, sense_id: int | None) -> None:
        word = self._word(word_id)
        if (word.entry_id, word.sense_id) != (entry_id, sense_id):
            word.entry_id = entry_id
            word.sense_id = sense_id
            self.touch()

    def unlink_word(self, word_id: int) -> None:
        word = self._word(word_id)
        if word.entry_id is not None or word.sense_id is not None:
            word.entry_id = None
            word.sense_id = None
            self.touch()

    def analyze_word(
        self,
        word_id: int,
        lemma: str,
        reading: str,
        pos: Sequence[str],
        inflection: Inflection | None,
    ) -> None:
        """Store what the analyzer says about a word with a span."""
        self.analyze_word_at(self._position(word_id), lemma, reading, pos, inflection)

    def analyze_word_at(
        self,
        position: int,
        lemma: str,
        reading: str,
        pos: Sequence[str],
        inflection: Inflection | None,
    ) -> None:
        """`analyze_word` for the word at `position`."""
        word = self.words[position]
        if not word.has_span:
            raise SentenceWordError("only a word with a span can be analyzed")
        values = (lemma, reading, list(pos), inflection)
        if (word.lemma, word.reading, word.pos, word.inflection) != values:
            word.lemma, word.reading, word.pos, word.inflection = values
            self.touch()

    def correct_word(self, word_id: int, lemma: str, reading: str) -> None:
        """The user's own lemma and reading of a word (the analyzer's can be
        wrong: 今日, 方)."""
        word = self._word(word_id)
        lemma = lemma.strip()
        if not lemma:
            raise SentenceWordError("a word's lemma can't be empty")
        try:
            reading = clean_kana(reading)
        except ValueError as error:
            raise SentenceWordError(str(error)) from error
        if (word.lemma, word.reading) != (lemma, reading):
            word.lemma = lemma
            word.reading = reading
            self.touch()

    def _word(self, word_id: int) -> SentenceWord:
        return find_item(self.words, word_id, "sentence word")

    def _position(self, word_id: int) -> int:
        word = self._word(word_id)
        return next(i for i, w in enumerate(self.words) if w is word)

    def _set_words(self, words: list[SentenceWord]) -> None:
        # Checked first: a failed assignment would still be applied.
        _check_spans(self.text, words)
        self.words = words
        self.touch()


def _check_spans(text: str, words: Sequence[SentenceWord]) -> None:
    """Every span inside `text`, and no two overlapping."""
    spans = sorted(
        (w.start, w.end) for w in words if w.start is not None and w.end is not None
    )
    if spans and max(end for _, end in spans) > len(text):
        raise SentenceWordError("a word's span is outside the sentence")
    for (_, end), (start, _) in pairwise(spans):
        if start < end:
            raise SentenceWordError("two words of a sentence can't overlap")


def _changed(word: SentenceWord, **changes: object) -> SentenceWord:
    """A validated copy of `word` with `changes` (`model_copy` skips checks)."""
    return SentenceWord.model_validate({**word.model_dump(), **changes})


def _unanalyzed(word: SentenceWord, start: int | None, end: int | None) -> SentenceWord:
    """`word` at another span, without the analysis of the old one."""
    return _changed(
        word, start=start, end=end, lemma=None, reading=None, pos=[], inflection=None
    )


def _translations(
    current: Sequence[SentenceTranslation], translation: str | None, lang: str
) -> list[SentenceTranslation]:
    """The translation in `lang` (none when blank) first, then the others
    already there, in their order."""
    if lang == JAPANESE:
        raise ValueError("a translation can't be in Japanese")
    others = [t for t in current if t.lang != lang]
    translation = (translation or "").strip()
    if translation:
        return [SentenceTranslation(lang=lang, text=translation), *others]
    return others


def _relocated(words: Sequence[SentenceWord], old: str, new: str) -> list[SentenceWord]:
    """The words after the sentence's text changed from `old` to `new`."""
    result: list[SentenceWord] = []
    taken: list[tuple[int, int]] = []
    for word in words:
        if word.start is None or word.end is None:
            result.append(word)
            continue
        surface = old[word.start : word.end]
        start = (
            word.start
            if new[word.start : word.end] == surface
            and _free(word.start, word.end, taken)
            else _free_occurrence(new, surface, taken)
        )
        if start is None:
            result.append(_unanalyzed(word, None, None))
            continue
        taken.append((start, start + len(surface)))
        result.append(_changed(word, start=start, end=start + len(surface)))
    return result


def _free_occurrence(
    text: str, surface: str, taken: Sequence[tuple[int, int]]
) -> int | None:
    """The first place of `surface` in `text` that overlaps no taken span."""
    start = text.find(surface)
    while start >= 0:
        if _free(start, start + len(surface), taken):
            return start
        start = text.find(surface, start + 1)
    return None


def _free(start: int, end: int, taken: Sequence[tuple[int, int]]) -> bool:
    return all(end <= s or start >= e for s, e in taken)
