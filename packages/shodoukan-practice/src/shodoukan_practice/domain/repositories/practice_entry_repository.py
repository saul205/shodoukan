"""Port for the user's imported entries: loading, searching (also within a
collection) and storing them."""

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from ..entities import EntryCollection, PracticeEntry
from ..searches import LibrarySearch, SearchScope


class PracticeEntryRepository(Protocol):
    def get(self, entry_id: int, user_id: UUID) -> PracticeEntry | None: ...

    def get_many(self, ids: Iterable[int], user_id: UUID) -> list[PracticeEntry]: ...

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
