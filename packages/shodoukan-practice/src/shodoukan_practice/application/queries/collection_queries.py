"""Read use cases over a user's collections and their items."""

from uuid import UUID

from ...domain.entities import (
    EntryCollection,
    KanjiCollection,
    SharedEntryCollection,
    SharedKanjiCollection,
)
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import (
    EntryCollectionRepository,
    KanjiCollectionRepository,
    PracticeEntryRepository,
    PracticeKanjiRepository,
)
from ...domain.searches import InCollection, LibrarySearch

# Every item, active or not: an export is the whole collection.
_EVERY_ITEM = LibrarySearch()


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


class ExportEntryCollection:
    """One of the user's entry collections in its portable form: its items, in
    the order they were added, each with the user's own data.

    Raises `EntityNotFoundError` for a collection the user doesn't have, and
    `ValidationError` for one with more items than an import takes
    (`MAX_SHARED_ITEMS`).
    """

    def __init__(
        self,
        collections: EntryCollectionRepository,
        entries: PracticeEntryRepository,
    ) -> None:
        self._collections = collections
        self._entries = entries

    def execute(self, user_id: UUID, collection_id: int) -> SharedEntryCollection:
        collection = GetEntryCollection(self._collections).execute(
            user_id, collection_id
        )
        scope = InCollection(collection)
        total = self._entries.count(user_id, _EVERY_ITEM, scope)
        items = self._entries.find(user_id, _EVERY_ITEM, scope, total, 0)
        return SharedEntryCollection(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            items=[item.to_shared() for item in items],
        )


class ExportKanjiCollection:
    """One of the user's kanji collections in its portable form. Same rules
    as `ExportEntryCollection`."""

    def __init__(
        self,
        collections: KanjiCollectionRepository,
        kanji: PracticeKanjiRepository,
    ) -> None:
        self._collections = collections
        self._kanji = kanji

    def execute(self, user_id: UUID, collection_id: int) -> SharedKanjiCollection:
        collection = GetKanjiCollection(self._collections).execute(
            user_id, collection_id
        )
        scope = InCollection(collection)
        total = self._kanji.count(user_id, _EVERY_ITEM, scope)
        items = self._kanji.find(user_id, _EVERY_ITEM, scope, total, 0)
        return SharedKanjiCollection(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            items=[item.to_shared() for item in items],
        )
