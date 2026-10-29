"""Frozen snapshot of a shodoukan Entry, plus the mutable practice state
(enabled/disabled, added items, notes) layered on top.

The dictionary's data is never edited or removed: the user disables what
they don't want, and adds, edits and removes senses and meanings of their
own. A word's example sentences aren't part of it: they're sentences of the
library linked to it (`practice_sentence_entity.py`).
"""

from collections.abc import Iterable, Sequence
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field

from ..exceptions import (
    EntityNotFoundError,
    LastMeaningError,
    LastReadingError,
    OriginalDataError,
    SenseLanguageError,
)
from .nested_item_lookup import (
    Copyable,
    PartKind,
    SourceRef,
    Toggleable,
    brought_by,
    clean_kana,
    clean_meaning,
    clean_spelling,
    dismissal_key,
    dismissed_of,
    find_item,
    identity,
    merge_parts,
    prune_parts,
    unclaimed,
    untouched_from,
    version_row,
)
from .notes_value import Notes, parse_notes
from .shared_collection_value import (
    SharedEntry,
    SharedMeaning,
    SharedReading,
    SharedSense,
    SharedSpelling,
)
from .timestamped_entity import TimestampedEntity

# The parts of an entry the user can enable or disable, one item at a time.
EntryPart = Literal["kanji_readings", "readings", "senses", "glosses"]
Origin = Literal["imported", "added"]

# Sentences store the Japanese one under this language, like JMDict's.
JAPANESE = "jpn"


class PracticeGloss(BaseModel):
    id: int | None
    text: str
    lang: str
    type: str | None
    enabled: bool = True
    origin: Origin = "imported"
    # Where a copy came from (see `shared_collection_value`): the part all
    # its copies share, the row it was copied from, the version of its
    # content, and the collections that bring it (an update from one of them
    # lets go of it; it's removed when none does). `None` is this row
    # itself. No links: the origin may be gone.
    original_id: int | None = None
    source_id: int | None = None
    edited_id: int | None = None
    revision: int = 0
    source_collection_ids: list[SourceRef] = Field(default_factory=list)


class PracticeSense(BaseModel):
    id: int | None
    pos: list[str]
    misc: list[str]
    dialects: list[str]
    info: list[str]
    glosses: list[PracticeGloss]
    notes: Notes = None
    # A disabled sense hides its glosses without changing their own flags, so
    # enabling it again brings it back as it was.
    enabled: bool = True
    origin: Origin = "imported"
    # A container: its identity only; its parts carry their versions.
    original_id: int | None = None
    source_id: int | None = None


class PracticeReading(BaseModel):
    id: int | None
    text: str
    no_kanji: bool
    info: list[str]
    restricted_to: list[str]
    enabled: bool = True
    origin: Origin = "imported"
    original_id: int | None = None
    source_id: int | None = None
    edited_id: int | None = None
    revision: int = 0
    source_collection_ids: list[SourceRef] = Field(default_factory=list)


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
    original_id: int | None = None
    source_id: int | None = None
    edited_id: int | None = None
    revision: int = 0
    source_collection_ids: list[SourceRef] = Field(default_factory=list)


class PracticeEntry(TimestampedEntity):
    id: int | None
    user_id: UUID
    # The sole reference back to shodoukan's Entry.id; None for a word the
    # user created themselves.
    source_entry_id: int | None
    # For a word of the user's own copied from someone's collection: the
    # word all its copies share, and the row it was copied from.
    original_id: int | None = None
    source_id: int | None = None
    kanji_readings: list[PracticeKanjiReading]
    readings: list[PracticeReading]
    senses: list[PracticeSense]
    jlpt: int | None
    is_common: bool
    is_active: bool = True
    notes: Notes = None
    # Copied parts the user deleted, by kind and identity (`"gloss:12"`):
    # imports and updates from their source don't bring them back.
    dismissed_parts: list[str] = Field(default_factory=list)

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

    @classmethod
    def from_shared(
        cls,
        user_id: UUID,
        shared: SharedEntry,
        source_collection_id: SourceRef | None = None,
    ) -> Self:
        """A copy of someone's word of their own (`shared` has no source).

        Everything in it is the user's (`origin="added"`), with the origin's
        flags, and it remembers the word it was copied from.
        """
        if shared.source_entry_id is not None:
            raise ValueError("only a word of the user's own is copied whole")
        entry = cls(
            id=None,
            user_id=user_id,
            source_entry_id=None,
            original_id=shared.identity,
            source_id=shared.id,
            kanji_readings=[],
            readings=[],
            senses=[],
            jlpt=None,
            is_common=False,
        )
        entry.merge_shared(
            shared, created=True, source_collection_id=source_collection_id
        )
        return entry

    @property
    def is_own(self) -> bool:
        """Created by the user rather than imported from the dictionary."""
        return self.source_entry_id is None

    @property
    def identity(self) -> int | None:
        """For a word of the user's own: the word all its copies share."""
        return identity(self)

    @property
    def shared_key(self) -> str:
        """What the word is across libraries: its dictionary entry, or the
        identity of a word of someone's own (`SharedEntry.key`)."""
        if self.source_entry_id is not None:
            return f"entry:{self.source_entry_id}"
        return f"own:{self.identity}"

    def to_shared(self, include_notes: bool = True) -> SharedEntry:
        """What this word carries in an exported collection; its notes (and
        its senses') only with `include_notes`."""
        return SharedEntry(
            id=self.id,
            original_id=self.identity,
            source_entry_id=self.source_entry_id,
            is_active=self.is_active,
            notes=self.notes if include_notes else None,
            spellings=[
                SharedSpelling(
                    origin=s.origin,
                    id=s.id,
                    original_id=identity(s),
                    edited_id=version_row(s),
                    revision=s.revision,
                    enabled=s.enabled,
                    text=s.kanji,
                )
                for s in self.kanji_readings
            ],
            readings=[
                SharedReading(
                    origin=r.origin,
                    id=r.id,
                    original_id=identity(r),
                    edited_id=version_row(r),
                    revision=r.revision,
                    enabled=r.enabled,
                    text=r.text,
                )
                for r in self.readings
            ],
            senses=[_shared_sense(s, include_notes) for s in self.senses],
        )

    def merge_shared(
        self,
        shared: SharedEntry,
        created: bool,
        source_collection_id: SourceRef | None = None,
    ) -> bool:
        """Take what a shared copy of this word adds.

        The user's data wins: the parts they added that this word doesn't
        have in that version are appended (another version of one it has is
        added next to it), notes are copied only where there are none,
        and the flags (`enabled`, `is_active`) are taken only when the word
        was `created` by this import. Imported parts are located by place and
        checked by text; one that doesn't match (the dictionary changed) is
        left alone, with the parts the user added to it. An added meaning in
        another language than its sense's is skipped. The copies remember
        `source_collection_id`, the collection they came with. Returns
        whether anything changed.
        """
        changed = False
        if created and self.is_active != shared.is_active:
            self.is_active = shared.is_active
            changed = True
        if self.notes is None and shared.notes is not None:
            self.notes = shared.notes
            changed = True
        changed |= merge_parts(
            self.kanji_readings,
            shared.spellings,
            created=created,
            same=lambda target, part: target.kanji == part.text,
            copy=lambda part: _copied_spelling(part, source_collection_id),
            source=source_collection_id,
            dismissed=dismissed_of(self.dismissed_parts, "spelling"),
        )
        changed |= merge_parts(
            self.readings,
            shared.readings,
            created=created,
            same=lambda target, part: target.text == part.text,
            copy=lambda part: _copied_reading(part, source_collection_id),
            source=source_collection_id,
            dismissed=dismissed_of(self.dismissed_parts, "reading"),
        )
        changed |= self._merge_senses(shared.senses, created, source_collection_id)
        if changed:
            self.touch()
        return changed

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
        """Show or hide one reading, spelling, sense or meaning."""
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
        """Remove one of the user's own senses, with its meanings."""
        sense = self._sense(sense_id)
        if sense.origin == "imported":
            raise OriginalDataError("dictionary senses can only be disabled")
        self.senses.remove(sense)
        self._dismiss("sense", sense)
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
        self._dismiss("spelling", spelling)
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
        self._dismiss("reading", reading)
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
            gloss.edited_id = None  # this version is now the user's
            gloss.revision += 1
            self.touch()

    def remove_gloss(self, gloss_id: int) -> None:
        """Remove one of the user's own meanings.

        A sense keeps at least one (`LastMeaningError`): without one it would
        show in no language, nor could its note be reached. To
        get rid of an own sense, remove the sense.
        """
        sense, gloss = self._own_gloss(gloss_id)
        if len(sense.glosses) == 1:
            raise LastMeaningError("a sense keeps at least one meaning")
        sense.glosses.remove(gloss)
        self._dismiss("gloss", gloss)
        self.touch()

    def prune_source(self, shared: SharedEntry, source_collection_id: int) -> bool:
        """Remove what that collection brought, untouched, and no longer has.

        Untouched means added with the collection and not edited since; what
        the user edited or added stays, and so does what another collection
        the user follows still brings (the collection only lets go of it). A
        word keeps one reading and a sense one meaning. An own sense the
        collection dropped goes whole only when nothing in it is the user's
        or brought by another collection, and it has no notes. Returns
        whether anything changed.
        """
        source = source_collection_id
        changed = prune_parts(self.kanji_readings, shared.spellings, source)
        changed |= prune_parts(self.readings, shared.readings, source, keep=1)
        imported = [s for s in self.senses if s.origin == "imported"]
        shared_imported = [s for s in shared.senses if s.origin == "imported"]
        for target, part in zip(imported, shared_imported, strict=False):
            if _same_sense(target, part):
                changed |= _prune_sense_parts(target, part, source)
        added = {s.identity: s for s in shared.senses if s.origin == "added"}
        for sense in [s for s in self.senses if s.origin == "added"]:
            shared_sense = added.get(identity(sense))
            if shared_sense is not None:
                changed |= _prune_sense_parts(sense, shared_sense, source)
            elif sense.source_id is not None and _brings(sense, source):
                changed |= _prune_sense_parts(sense, None, source)
                if _left_over(sense):
                    self.senses.remove(sense)
                    changed = True
        if changed:
            self.touch()
        return changed

    def shared_sense_ids(self, shared: SharedEntry) -> list[int | None]:
        """For each sense of a shared copy of this word, the id of the
        user's sense it is, or `None`: imported senses by place (checked by
        their first meaning), own ones by identity. What a sentence that came
        with a shared sense is linked to."""
        imported = [s for s in self.senses if s.origin == "imported"]
        position = 0
        ids: list[int | None] = []
        for part in shared.senses:
            if part.origin == "imported":
                target = imported[position] if position < len(imported) else None
                position += 1
                same = target is not None and _same_sense(target, part)
                ids.append(target.id if target is not None and same else None)
            else:
                ids.append(
                    next(
                        (
                            s.id
                            for s in self.senses
                            if part.identity is not None
                            and identity(s) == part.identity
                        ),
                        None,
                    )
                )
        return ids

    def dismiss_example(self, sentence: Copyable) -> bool:
        """Remember a copied sentence the user removed, so the word's source
        doesn't bring it back. Sentences keep the `example` kind: they travel
        as the word's examples. Returns whether anything changed."""
        before = len(self.dismissed_parts)
        self._dismiss("example", sentence)
        if len(self.dismissed_parts) == before:
            return False
        self.touch()
        return True

    def _dismiss(self, kind: PartKind, part: Copyable) -> None:
        """Remember a deleted copy, so its source doesn't bring it back."""
        key = dismissal_key(kind, part)
        if key is not None and key not in self.dismissed_parts:
            self.dismissed_parts.append(key)

    def _merge_senses(
        self, shared: list[SharedSense], created: bool, source: SourceRef | None
    ) -> bool:
        imported = [s for s in self.senses if s.origin == "imported"]
        position = 0
        changed = False
        for part in shared:
            target: PracticeSense | None
            if part.origin == "imported":
                target = imported[position] if position < len(imported) else None
                position += 1
                if target is None or not _same_sense(target, part):
                    continue
                if created and target.enabled != part.enabled:
                    target.enabled = part.enabled
                    changed = True
            elif part.identity in dismissed_of(self.dismissed_parts, "sense"):
                continue
            else:
                target = next(
                    (
                        s
                        for s in self.senses
                        if part.identity is not None and identity(s) == part.identity
                    ),
                    None,
                )
                if target is None:
                    target = _copied_sense(part)
                    self.senses.append(target)
                    changed = True
            changed |= _merge_sense_parts(
                target, part, created, source, self.dismissed_parts
            )
        return changed

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
        return [g for s in self.senses for g in s.glosses]


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
        origin="added",
    )


def _shared_meaning(gloss: PracticeGloss) -> SharedMeaning:
    return SharedMeaning(
        origin=gloss.origin,
        id=gloss.id,
        original_id=identity(gloss),
        edited_id=version_row(gloss),
        revision=gloss.revision,
        enabled=gloss.enabled,
        text=gloss.text,
        lang=gloss.lang,
    )


def _shared_sense(sense: PracticeSense, include_notes: bool) -> SharedSense:
    return SharedSense(
        origin=sense.origin,
        id=sense.id,
        original_id=identity(sense),
        enabled=sense.enabled,
        notes=sense.notes if include_notes else None,
        glosses=[_shared_meaning(g) for g in sense.glosses],
    )


def _same_sense(target: PracticeSense, part: SharedSense) -> bool:
    """Whether an imported sense is the shared one: same first meaning."""
    ours = [g.text for g in target.glosses if g.origin == "imported"][:1]
    theirs = [g.text for g in part.glosses if g.origin == "imported"][:1]
    return ours == theirs


def _merge_sense_parts(
    target: PracticeSense,
    part: SharedSense,
    created: bool,
    source: SourceRef | None,
    dismissed: list[str],
) -> bool:
    """Notes and meanings of a shared sense into the user's one (its
    examples are sentences: `sentence_sharing_service`)."""
    changed = False
    if target.notes is None and part.notes is not None:
        target.notes = part.notes
        changed = True
    # A sense's meanings are all in one language (that of its first).
    lang = target.glosses[0].lang if target.glosses else None
    changed |= merge_parts(
        target.glosses,
        [g for g in part.glosses if g.origin == "imported" or lang in (None, g.lang)],
        created=created,
        same=lambda ours, theirs: ours.text == theirs.text,
        copy=lambda gloss: _copied_gloss(gloss, source),
        source=source,
        dismissed=dismissed_of(dismissed, "gloss"),
    )
    return changed


def _copied_spelling(
    part: SharedSpelling, source_collection_id: SourceRef | None
) -> PracticeKanjiReading:
    return PracticeKanjiReading(
        id=None,
        kanji=clean_spelling(part.text),
        info=[],
        enabled=part.enabled,
        origin="added",
        original_id=part.identity,
        source_id=part.id,
        edited_id=part.edited_id if part.edited_id is not None else part.id,
        revision=part.revision,
        source_collection_ids=brought_by(source_collection_id),
    )


def _copied_reading(
    part: SharedReading, source_collection_id: SourceRef | None
) -> PracticeReading:
    return PracticeReading(
        id=None,
        text=clean_kana(part.text),
        no_kanji=False,
        info=[],
        restricted_to=[],
        enabled=part.enabled,
        origin="added",
        original_id=part.identity,
        source_id=part.id,
        edited_id=part.edited_id if part.edited_id is not None else part.id,
        revision=part.revision,
        source_collection_ids=brought_by(source_collection_id),
    )


def _copied_gloss(
    part: SharedMeaning, source_collection_id: SourceRef | None
) -> PracticeGloss:
    return PracticeGloss(
        id=None,
        text=clean_meaning(part.text),
        lang=part.lang,
        type=None,
        enabled=part.enabled,
        origin="added",
        original_id=part.identity,
        source_id=part.id,
        edited_id=part.edited_id if part.edited_id is not None else part.id,
        revision=part.revision,
        source_collection_ids=brought_by(source_collection_id),
    )


def _copied_sense(part: SharedSense) -> PracticeSense:
    """An empty sense of the user's own; its meanings follow."""
    return PracticeSense(
        id=None,
        pos=[],
        misc=[],
        dialects=[],
        info=[],
        glosses=[],
        enabled=part.enabled,
        origin="added",
        original_id=part.identity,
        source_id=part.id,
    )


def _prune_sense_parts(
    target: PracticeSense, part: SharedSense | None, source: int
) -> bool:
    """Prune a sense's meanings (keeping one) against the shared sense, or
    against nothing when the collection dropped it."""
    glosses = part.glosses if part else []
    return prune_parts(target.glosses, glosses, source, keep=1)


def _brings(sense: PracticeSense, source: int) -> bool:
    """Whether the collection brings something in the sense: only then can
    it drop the sense (one it never brought isn't its to remove)."""
    return any(untouched_from(g, source) for g in sense.glosses)


def _left_over(sense: PracticeSense) -> bool:
    """Whether nothing in an own sense is the user's or brought by a
    collection any more: no notes, and every part an unclaimed copy."""
    return sense.notes is None and all(unclaimed(g) for g in sense.glosses)
