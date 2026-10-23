"""Find a user's collection or fail, for the use cases that write to one.

Scoped to the user, so someone else's collection is "not found" too.
"""

from uuid import UUID

from ...domain.entities import EntryCollection, KanjiCollection
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import (
    EntryCollectionRepository,
    KanjiCollectionRepository,
)


def entry_collection(
    collections: EntryCollectionRepository, collection_id: int, user_id: UUID
) -> EntryCollection:
    collection = collections.get(collection_id, user_id)
    if collection is None:
        raise EntityNotFoundError(f"entry collection {collection_id} not found")
    return collection


def kanji_collection(
    collections: KanjiCollectionRepository, collection_id: int, user_id: UUID
) -> KanjiCollection:
    collection = collections.get(collection_id, user_id)
    if collection is None:
        raise EntityNotFoundError(f"kanji collection {collection_id} not found")
    return collection
