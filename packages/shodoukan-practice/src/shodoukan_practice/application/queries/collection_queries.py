"""Read use cases over a user's collections and their items."""

from uuid import UUID

from ...domain.entities import (
    EntryCollection,
    KanjiCollection,
)
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import (
    EntryCollectionRepository,
    KanjiCollectionRepository,
)


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
