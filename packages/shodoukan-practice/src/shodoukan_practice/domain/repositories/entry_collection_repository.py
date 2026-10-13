"""Port for entry collections and their membership (link table)."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from ..entities import EntryCollection, PracticeEntry, SharedEntryCollection
from ..searches import PublicCollectionSearch, PublicCollectionSummary


class EntryCollectionRepository(Protocol):
    def get(self, collection_id: int, user_id: UUID) -> EntryCollection | None: ...

    def list_for_user(self, user_id: UUID) -> list[EntryCollection]: ...

    def list_for_item(self, entry: PracticeEntry) -> list[EntryCollection]:
        """Collections the entry belongs to (its tags)."""
        ...

    def add_item(
        self,
        collection: EntryCollection,
        entry: PracticeEntry,
        from_source: bool = False,
    ) -> None:
        """Link the item; a no-op if it's linked already. `from_source`: the
        collection's source put it there (an import), so an update from that
        source may take it out."""
        ...

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

    # --- Sharing ---

    def save_publication(
        self,
        collection: EntryCollection,
        shared: SharedEntryCollection,
        includes_notes: bool,
    ) -> None:
        """Store `shared` as the collection's published snapshot, replacing
        the previous one (only the latest version is kept)."""
        ...

    def get_publication(
        self, collection: EntryCollection
    ) -> SharedEntryCollection | None:
        """The collection's published snapshot, if it was ever published."""
        ...

    def get_public(self, collection_id: int) -> EntryCollection | None:
        """The collection if it's public, whoever owns it."""
        ...

    def find_public(
        self,
        search: PublicCollectionSearch,
        viewer_id: UUID,
        limit: int,
        offset: int,
    ) -> list[PublicCollectionSummary[EntryCollection]]:
        """Public collections matching `search`, in its order, paginated."""
        ...

    def count_public(self, search: PublicCollectionSearch, viewer_id: UUID) -> int:
        """How many collections `find_public` pages through."""
        ...

    def public_summary(
        self, collection: EntryCollection, viewer_id: UUID
    ) -> PublicCollectionSummary[EntryCollection]:
        """A public collection's owner and counts, as `find_public` lists it."""
        ...

    def record_download(
        self, collection: EntryCollection, user_id: UUID, version: int
    ) -> None:
        """Remember that `user_id` imported `version` of it. One row per user,
        keeping the latest version; safe against concurrent first imports."""
        ...
