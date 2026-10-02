"""Port for entry collections and their membership (link table)."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from ..entities import EntryCollection, PracticeEntry


class EntryCollectionRepository(Protocol):
    def get(self, collection_id: int, user_id: UUID) -> EntryCollection | None: ...

    def list_for_user(self, user_id: UUID) -> list[EntryCollection]: ...

    def list_for_item(self, entry: PracticeEntry) -> list[EntryCollection]:
        """Collections the entry belongs to (its tags)."""
        ...

    def add_item(self, collection: EntryCollection, entry: PracticeEntry) -> None: ...

    def remove_item(
        self, collection: EntryCollection, entry: PracticeEntry
    ) -> None: ...

    def item_ids(self, collections: Sequence[EntryCollection]) -> set[int]:
        """Distinct entry ids across the collections."""
        ...

    def add(self, collection: EntryCollection) -> EntryCollection:
        """Raises `CollectionNameTakenError` if the user has that name already."""
        ...

    def update(self, collection: EntryCollection) -> EntryCollection:
        """Raises `CollectionNameTakenError` if the user has that name already."""
        ...

    def delete(self, collection: EntryCollection) -> None: ...
