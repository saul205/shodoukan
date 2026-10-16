"""Port for kanji collections and their membership (link table)."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from ..entities import KanjiCollection, PracticeKanji, SharedKanjiCollection
from ..searches import PublicCollectionSearch, PublicCollectionSummary


class KanjiCollectionRepository(Protocol):
    def get(self, collection_id: int, user_id: UUID) -> KanjiCollection | None: ...

    def list_for_user(self, user_id: UUID) -> list[KanjiCollection]: ...

    def list_for_item(self, kanji: PracticeKanji) -> list[KanjiCollection]:
        """Collections the kanji belongs to (its tags)."""
        ...

    def add_item(
        self,
        collection: KanjiCollection,
        kanji: PracticeKanji,
        from_source: bool = False,
    ) -> None:
        """Link the item; a no-op if it's linked already. `from_source`: the
        collection's source put it there (an import), so an update from that
        source may take it out."""
        ...

    def remove_item(
        self, collection: KanjiCollection, kanji: PracticeKanji
    ) -> None: ...

    def item_ids(self, collections: Sequence[KanjiCollection]) -> set[int]:
        """Distinct kanji ids across the collections."""
        ...

    def add(self, collection: KanjiCollection) -> KanjiCollection:
        """Raises `CollectionNameTakenError` if the user has that name already."""
        ...

    def update(self, collection: KanjiCollection) -> KanjiCollection:
        """Raises `CollectionNameTakenError` if the user has that name already."""
        ...

    def delete(self, collection: KanjiCollection) -> None: ...

    # --- Sharing ---

    def save_publication(
        self,
        collection: KanjiCollection,
        shared: SharedKanjiCollection,
        includes_notes: bool,
    ) -> None:
        """Store `shared` as the collection's published snapshot, replacing
        the previous one (only the latest version is kept)."""
        ...

    def get_publication(
        self, collection: KanjiCollection
    ) -> SharedKanjiCollection | None:
        """The collection's published snapshot, if it was ever published."""
        ...

    def get_public(self, collection_id: int) -> KanjiCollection | None:
        """The collection if it's public, whoever owns it."""
        ...

    def find_public(
        self,
        search: PublicCollectionSearch,
        viewer_id: UUID,
        limit: int,
        offset: int,
    ) -> list[PublicCollectionSummary[KanjiCollection]]:
        """Public collections matching `search`, in its order, paginated."""
        ...

    def count_public(self, search: PublicCollectionSearch, viewer_id: UUID) -> int:
        """How many collections `find_public` pages through."""
        ...

    def public_summary(
        self, collection: KanjiCollection, viewer_id: UUID
    ) -> PublicCollectionSummary[KanjiCollection]:
        """A public collection's owner and counts, as `find_public` lists it."""
        ...

    def record_download(
        self, collection: KanjiCollection, user_id: UUID, version: int
    ) -> None:
        """Remember that `user_id` imported `version` of it. One row per user,
        keeping the latest version; safe against concurrent first imports."""
        ...

    # --- Following a source ---

    def is_from_source(self, collection: KanjiCollection, kanji: PracticeKanji) -> bool:
        """Whether the collection's source put the item there."""
        ...

    def source_item_ids(self, collection: KanjiCollection) -> set[int]:
        """Ids of the items the collection's source put there."""
        ...

    def dismiss_item(self, collection: KanjiCollection, key: str) -> None:
        """Remember that the user took the item with that shared key out of a
        copy, so updates from its source don't bring it back. Idempotent."""
        ...

    def undismiss_item(self, collection: KanjiCollection, key: str) -> bool:
        """Forget a dismissal; whether there was one."""
        ...

    def dismissed_items(self, collection: KanjiCollection) -> set[str]:
        """The shared keys `dismiss_item` remembered for the collection."""
        ...

    def latest_source_versions(self, user_id: UUID) -> dict[int, int]:
        """`{collection id: its source's published version}` for the user's
        copies whose source is still public."""
        ...
