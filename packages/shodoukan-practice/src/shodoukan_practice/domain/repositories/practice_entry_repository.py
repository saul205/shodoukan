"""Port for the user's imported entries, including reads through a collection."""

from collections.abc import Iterable
from typing import Protocol

from ..entities import EntryCollection, PracticeEntry


class PracticeEntryRepository(Protocol):
    def get(self, entry_id: int, user_id: int) -> PracticeEntry | None: ...

    def get_many(self, ids: Iterable[int], user_id: int) -> list[PracticeEntry]: ...

    def list_by_collection(
        self, collection: EntryCollection, limit: int, offset: int
    ) -> list[PracticeEntry]:
        """Active entries in the collection, paginated in the database."""
        ...

    def add(self, entry: PracticeEntry) -> PracticeEntry: ...

    def update(self, entry: PracticeEntry) -> PracticeEntry: ...
