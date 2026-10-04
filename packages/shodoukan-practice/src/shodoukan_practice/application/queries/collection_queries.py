"""Read use cases over a user's collections and their items."""

from uuid import UUID

from ...domain.entities import (
    EntryCollection,
    KanjiCollection,
    PracticeEntry,
    PracticeKanji,
)
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import (
    EntryCollectionRepository,
    KanjiCollectionRepository,
    PracticeEntryRepository,
    PracticeKanjiRepository,
)
from .library_queries import LibraryPage


class ListEntryCollections:
    """The user's entry collections, by name."""

    def __init__(self, collections: EntryCollectionRepository) -> None:
        self._collections = collections

    def execute(self, user_id: UUID) -> list[EntryCollection]:
        return self._collections.list_for_user(user_id)


class ListKanjiCollections:
    """The user's kanji collections, by name."""

    def __init__(self, collections: KanjiCollectionRepository) -> None:
        self._collections = collections

    def execute(self, user_id: UUID) -> list[KanjiCollection]:
        return self._collections.list_for_user(user_id)


class GetEntryCollection:
    """One of the user's entry collections; `EntityNotFoundError` otherwise."""

    def __init__(self, collections: EntryCollectionRepository) -> None:
        self._collections = collections

    def execute(self, user_id: UUID, collection_id: int) -> EntryCollection:
        collection = self._collections.get(collection_id, user_id)
        if collection is None:
            raise EntityNotFoundError(f"entry collection {collection_id} not found")
        return collection


class GetKanjiCollection:
    """One of the user's kanji collections; `EntityNotFoundError` otherwise."""

    def __init__(self, collections: KanjiCollectionRepository) -> None:
        self._collections = collections

    def execute(self, user_id: UUID, collection_id: int) -> KanjiCollection:
        collection = self._collections.get(collection_id, user_id)
        if collection is None:
            raise EntityNotFoundError(f"kanji collection {collection_id} not found")
        return collection


class ListEntryCollectionItems:
    """A page of a collection's entries, in the order they were added.

    Inactive ones are included unless `active` says otherwise, as in the
    library, so the collection page can show and reactivate them.
    """

    def __init__(
        self, collections: EntryCollectionRepository, entries: PracticeEntryRepository
    ) -> None:
        self._get = GetEntryCollection(collections)
        self._entries = entries

    def execute(
        self,
        user_id: UUID,
        collection_id: int,
        limit: int = 20,
        offset: int = 0,
        active: bool | None = None,
    ) -> LibraryPage[PracticeEntry]:
        collection = self._get.execute(user_id, collection_id)
        return LibraryPage(
            items=self._entries.list_by_collection(collection, limit, offset, active),
            total=self._entries.count_by_collection(collection, active),
            limit=limit,
            offset=offset,
        )


class ListKanjiCollectionItems:
    """A page of a collection's kanji (see `ListEntryCollectionItems`)."""

    def __init__(
        self, collections: KanjiCollectionRepository, kanji: PracticeKanjiRepository
    ) -> None:
        self._get = GetKanjiCollection(collections)
        self._kanji = kanji

    def execute(
        self,
        user_id: UUID,
        collection_id: int,
        limit: int = 20,
        offset: int = 0,
        active: bool | None = None,
    ) -> LibraryPage[PracticeKanji]:
        collection = self._get.execute(user_id, collection_id)
        return LibraryPage(
            items=self._kanji.list_by_collection(collection, limit, offset, active),
            total=self._kanji.count_by_collection(collection, active),
            limit=limit,
            offset=offset,
        )
