"""Port for the user's imported entries, including reads through a collection."""

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from ..entities import EntryCollection, PracticeEntry


class PracticeEntryRepository(Protocol):
    def get(self, entry_id: int, user_id: UUID) -> PracticeEntry | None: ...

    def get_many(self, ids: Iterable[int], user_id: UUID) -> list[PracticeEntry]: ...

    def list_by_collection(
        self, collection: EntryCollection, limit: int, offset: int
    ) -> list[PracticeEntry]:
        """Active entries in the collection, paginated in the database."""
        ...

    def get_by_source_entry_id(
        self, source_entry_id: int, user_id: UUID
    ) -> PracticeEntry | None:
        """The user's copy of dictionary entry `source_entry_id`, if imported."""
        ...

    def add(self, entry: PracticeEntry) -> PracticeEntry: ...

    def add_if_absent(self, entry: PracticeEntry) -> tuple[PracticeEntry, bool]:
        """Store `entry` unless the user already has it.

        Returns the stored item and whether it was created. Safe against a
        concurrent import of the same item: the existing copy is returned.
        """
        ...

    def update(self, entry: PracticeEntry) -> PracticeEntry: ...
