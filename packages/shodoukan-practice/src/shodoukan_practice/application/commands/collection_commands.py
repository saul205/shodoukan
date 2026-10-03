"""Use cases that create, edit and fill a user's collections.

Entry and kanji collections get their own use cases: they never mix, and the
two kinds stay explicit until a third shows what to share. Collections and
items are looked up scoped to the user, so someone else's is "not found".
None of them commit; the caller owns the transaction.
"""

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
from .collection_lookups import entry_collection, kanji_collection


def _entry(
    entries: PracticeEntryRepository, entry_id: int, user_id: UUID
) -> PracticeEntry:
    entry = entries.get(entry_id, user_id)
    if entry is None:
        raise EntityNotFoundError(f"entry {entry_id} not found")
    return entry


def _kanji(
    kanji: PracticeKanjiRepository, kanji_id: int, user_id: UUID
) -> PracticeKanji:
    item = kanji.get(kanji_id, user_id)
    if item is None:
        raise EntityNotFoundError(f"kanji {kanji_id} not found")
    return item


# --- Create ---


class CreateEntryCollection:
    """Create an empty entry collection.

    Raises `CollectionNameTakenError` if the user has one with that name.
    """

    def __init__(self, collections: EntryCollectionRepository) -> None:
        self._collections = collections

    def execute(
        self, user_id: UUID, name: str, description: str | None = None
    ) -> EntryCollection:
        return self._collections.add(
            EntryCollection(
                id=None, user_id=user_id, name=name, description=description
            )
        )


class CreateKanjiCollection:
    """Create an empty kanji collection. Same rules as `CreateEntryCollection`."""

    def __init__(self, collections: KanjiCollectionRepository) -> None:
        self._collections = collections

    def execute(
        self, user_id: UUID, name: str, description: str | None = None
    ) -> KanjiCollection:
        return self._collections.add(
            KanjiCollection(
                id=None, user_id=user_id, name=name, description=description
            )
        )


# --- Update ---


class UpdateEntryCollection:
    """Replace an entry collection's name and description.

    Unchanged values leave `updated_at` alone. Raises `EntityNotFoundError`
    or `CollectionNameTakenError`.
    """

    def __init__(self, collections: EntryCollectionRepository) -> None:
        self._collections = collections

    def execute(
        self,
        user_id: UUID,
        collection_id: int,
        name: str,
        description: str | None,
    ) -> EntryCollection:
        collection = entry_collection(self._collections, collection_id, user_id)
        collection.rename(name)
        collection.describe(description)
        return self._collections.update(collection)


class UpdateKanjiCollection:
    """Replace a kanji collection's name and description (see the entry one)."""

    def __init__(self, collections: KanjiCollectionRepository) -> None:
        self._collections = collections

    def execute(
        self,
        user_id: UUID,
        collection_id: int,
        name: str,
        description: str | None,
    ) -> KanjiCollection:
        collection = kanji_collection(self._collections, collection_id, user_id)
        collection.rename(name)
        collection.describe(description)
        return self._collections.update(collection)


# --- Delete ---


class DeleteEntryCollection:
    """Delete an entry collection. Its entries stay in the library."""

    def __init__(self, collections: EntryCollectionRepository) -> None:
        self._collections = collections

    def execute(self, user_id: UUID, collection_id: int) -> None:
        collection = entry_collection(self._collections, collection_id, user_id)
        self._collections.delete(collection)


class DeleteKanjiCollection:
    """Delete a kanji collection. Its kanji stay in the library."""

    def __init__(self, collections: KanjiCollectionRepository) -> None:
        self._collections = collections

    def execute(self, user_id: UUID, collection_id: int) -> None:
        collection = kanji_collection(self._collections, collection_id, user_id)
        self._collections.delete(collection)


# --- Membership ---


class AddEntryToCollection:
    """Put a library entry in a collection (tag it). Idempotent."""

    def __init__(
        self, collections: EntryCollectionRepository, entries: PracticeEntryRepository
    ) -> None:
        self._collections = collections
        self._entries = entries

    def execute(self, user_id: UUID, collection_id: int, entry_id: int) -> None:
        collection = entry_collection(self._collections, collection_id, user_id)
        self._collections.add_item(collection, _entry(self._entries, entry_id, user_id))


class AddKanjiToCollection:
    """Put a library kanji in a collection (tag it). Idempotent."""

    def __init__(
        self, collections: KanjiCollectionRepository, kanji: PracticeKanjiRepository
    ) -> None:
        self._collections = collections
        self._kanji = kanji

    def execute(self, user_id: UUID, collection_id: int, kanji_id: int) -> None:
        collection = kanji_collection(self._collections, collection_id, user_id)
        self._collections.add_item(collection, _kanji(self._kanji, kanji_id, user_id))


class RemoveEntryFromCollection:
    """Take an entry out of a collection; it stays in the library. Idempotent."""

    def __init__(
        self, collections: EntryCollectionRepository, entries: PracticeEntryRepository
    ) -> None:
        self._collections = collections
        self._entries = entries

    def execute(self, user_id: UUID, collection_id: int, entry_id: int) -> None:
        collection = entry_collection(self._collections, collection_id, user_id)
        self._collections.remove_item(
            collection, _entry(self._entries, entry_id, user_id)
        )


class RemoveKanjiFromCollection:
    """Take a kanji out of a collection; it stays in the library. Idempotent."""

    def __init__(
        self, collections: KanjiCollectionRepository, kanji: PracticeKanjiRepository
    ) -> None:
        self._collections = collections
        self._kanji = kanji

    def execute(self, user_id: UUID, collection_id: int, kanji_id: int) -> None:
        collection = kanji_collection(self._collections, collection_id, user_id)
        self._collections.remove_item(
            collection, _kanji(self._kanji, kanji_id, user_id)
        )
