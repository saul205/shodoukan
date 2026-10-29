"""Port for the sentences of the user's library."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ..entities import Inflection, PracticeSentence


@dataclass(frozen=True)
class SentenceSearch:
    """Which of the user's sentences a list shows. `None` doesn't filter."""

    # Part of the sentence or of a translation, as typed.
    text: str | None = None
    # Sentences with a word linked to this entry.
    entry_id: int | None = None
    # True: with a linked word; False: none linked ("unlinked").
    linked: bool | None = None
    active: bool | None = None


@dataclass(frozen=True)
class GapText:
    """A word's gap as a sentence exercise reads it: only the columns a
    question uses, not the whole sentence (`gaps`)."""

    entry_id: int
    sentence_id: int
    sentence: str
    start: int
    end: int
    reading: str
    pos: str | None
    inflection: Inflection | None
    translation: str | None = None

    @property
    def surface(self) -> str:
        return self.sentence[self.start : self.end]

    @property
    def form(self) -> tuple[str | None, Inflection | None]:
        """What gaps must share to be options of each other."""
        return self.pos, self.inflection


class PracticeSentenceRepository(Protocol):
    def get(self, sentence_id: int, user_id: UUID) -> PracticeSentence | None: ...

    def for_entry(self, entry_id: int, user_id: UUID) -> list[PracticeSentence]:
        """The user's sentences with a word linked to entry `entry_id`, oldest
        first: "the sentences of a word"."""
        ...

    def gaps(
        self, entry_ids: Iterable[int], user_id: UUID, translation_lang: str
    ) -> list[GapText]:
        """The analyzed gaps of the entries in the user's active sentences,
        with each sentence's translation in `translation_lang` (if any):
        what a sentence exercise's pool reads. Columns only."""
        ...

    def for_entries(
        self, entry_ids: Iterable[int], user_id: UUID
    ) -> list[PracticeSentence]:
        """The user's sentences with a word linked to any of the entries,
        oldest first, each once: what an export of those words carries."""
        ...

    def by_versions(
        self, versions: Iterable[tuple[int, int]], user_id: UUID
    ) -> list[PracticeSentence]:
        """The user's sentences in one of `versions` (the row that wrote the
        content, and its revision): copies an import may already have."""
        ...

    def copies(self, user_id: UUID) -> list[PracticeSentence]:
        """The user's copies of someone's sentences (`source_id` set): what
        an update from a source may let go of."""
        ...

    def find(
        self, user_id: UUID, search: SentenceSearch, limit: int, offset: int
    ) -> list[PracticeSentence]:
        """The user's sentences matching `search`, newest first, paginated."""
        ...

    def count(self, user_id: UUID, search: SentenceSearch) -> int:
        """How many sentences `find` pages through."""
        ...

    def imported_by_text(
        self, texts: Iterable[str], user_id: UUID
    ) -> dict[str, PracticeSentence]:
        """The user's dictionary sentences among `texts`, by text: importing a
        word reuses a sentence the user already has from another word."""
        ...

    def needing_analysis(self, user_id: UUID) -> list[PracticeSentence]:
        """The user's sentences with a word to analyze: one with a span and
        no analysis, or one linked to a word but without a span."""
        ...

    def users_needing_analysis(self) -> list[UUID]:
        """The users with sentences `needing_analysis`. The one query across
        users: maintenance (`analyze-sentences`) goes user by user."""
        ...

    def add(self, sentence: PracticeSentence) -> PracticeSentence: ...

    def update(self, sentence: PracticeSentence) -> PracticeSentence:
        """Raises `EntityNotFoundError` if it isn't stored, or isn't the user's."""
        ...

    def delete(self, sentence: PracticeSentence) -> None: ...
