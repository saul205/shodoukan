"""Port for the user's imported entries: loading, searching (also within a
collection) and storing them."""

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..entities import EntryCollection, PracticeEntry
from ..searches import LibrarySearch, SearchScope


class EntryStudyText(BaseModel):
    """What an exercise studies of an entry: its enabled spellings and
    readings, and the enabled glosses in one language of each enabled sense
    that has any, all in order. A read model: an exercise's pool reads only
    this, never the whole entry."""

    model_config = ConfigDict(frozen=True)

    id: int
    spellings: tuple[str, ...]
    readings: tuple[str, ...]
    sense_glosses: tuple[tuple[str, ...], ...]


class PracticeEntryRepository(Protocol):
    def get(self, entry_id: int, user_id: UUID) -> PracticeEntry | None: ...

    def get_many(self, ids: Iterable[int], user_id: UUID) -> list[PracticeEntry]: ...

    def study_texts(
        self, ids: Iterable[int], user_id: UUID, meaning_lang: str
    ) -> list[EntryStudyText]:
        """`EntryStudyText` of the user's entries among `ids`, by id;
        `meaning_lang` as glosses store it (ISO 639-2, e.g. "eng")."""
        ...

    def find(
        self,
        user_id: UUID,
        search: LibrarySearch,
        scope: SearchScope[EntryCollection],
        limit: int,
        offset: int,
    ) -> list[PracticeEntry]:
        """The user's items that match `search` within `scope`, paginated.

        Best match first (`MatchTier`), then the scope's own order: most
        recently imported first in the library, the order they were added
        in a collection. Without text, only the scope and `active` filter.
        """
        ...

    def count(
        self, user_id: UUID, search: LibrarySearch, scope: SearchScope[EntryCollection]
    ) -> int:
        """How many items `find` pages through."""
        ...

    def get_by_source_entry_id(
        self, source_entry_id: int, user_id: UUID
    ) -> PracticeEntry | None:
        """The user's copy of dictionary entry `source_entry_id`, if imported."""
        ...

    def practice_ids_by_source_entry_id(
        self, source_entry_ids: Iterable[int], user_id: UUID
    ) -> dict[int, int]:
        """`{source_entry_id: practice id}` for the ones the user has imported.

        Lightweight: no snapshot is loaded.
        """
        ...

    def find_own_by_identity(
        self, identities: Iterable[int], user_id: UUID
    ) -> list[PracticeEntry]:
        """The user's own words (no source) whose identity (`original_id`, or
        their id when they're the original) is one of `identities`: the
        copies of a shared word the user already has."""
        ...

    def add(self, entry: PracticeEntry) -> PracticeEntry: ...

    def add_if_absent(self, entry: PracticeEntry) -> tuple[PracticeEntry, bool]:
        """Store `entry` unless the user already has it.

        Returns the stored item and whether it was created. Safe against a
        concurrent import of the same item: the existing copy is returned.
        """
        ...

    def update(self, entry: PracticeEntry) -> PracticeEntry: ...

    def delete(self, entry: PracticeEntry) -> None:
        """Remove it from the library, with its collection links.

        Raises `EntityNotFoundError` if it isn't stored for its user.
        """
        ...
