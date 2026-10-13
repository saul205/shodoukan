"""Use cases that create, edit and fill a user's collections.

Entry and kanji collections get their own use cases: they never mix, and the
two kinds stay explicit until a third shows what to share. Collections and
items are looked up scoped to the user, so someone else's is "not found".
None of them commit; the caller owns the transaction.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Generic, TypeVar
from uuid import UUID

from ...domain.entities import (
    FILE,
    EntryCollection,
    KanjiCollection,
    PracticeEntry,
    PracticeKanji,
    SharedEntry,
    SharedEntryCollection,
    SharedKanji,
    SharedKanjiCollection,
    SourceRef,
)
from ...domain.exceptions import EntityNotFoundError
from ...domain.gateways import DictionaryGateway
from ...domain.repositories import (
    EntryCollectionRepository,
    KanjiCollectionRepository,
    PracticeEntryRepository,
    PracticeKanjiRepository,
)
from ...domain.services import free_collection_name
from .collection_lookups import entry_collection, kanji_collection

C = TypeVar("C", EntryCollection, KanjiCollection)
R = TypeVar("R", int, str)


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
        entry = _entry(self._entries, entry_id, user_id)
        # Taken out of a copy: updates from its source won't bring it back.
        if collection.source_collection_id is not None and (
            self._collections.is_from_source(collection, entry)
        ):
            self._collections.dismiss_item(collection, entry.shared_key)
        self._collections.remove_item(collection, entry)


class RemoveKanjiFromCollection:
    """Take a kanji out of a collection; it stays in the library. Idempotent."""

    def __init__(
        self, collections: KanjiCollectionRepository, kanji: PracticeKanjiRepository
    ) -> None:
        self._collections = collections
        self._kanji = kanji

    def execute(self, user_id: UUID, collection_id: int, kanji_id: int) -> None:
        collection = kanji_collection(self._collections, collection_id, user_id)
        kanji = _kanji(self._kanji, kanji_id, user_id)
        # Taken out of a copy: updates from its source won't bring it back.
        if collection.source_collection_id is not None and (
            self._collections.is_from_source(collection, kanji)
        ):
            self._collections.dismiss_item(collection, kanji.shared_key)
        self._collections.remove_item(collection, kanji)


# --- Import ---


@dataclass
class CollectionImport(Generic[C, R]):
    """What importing a shared collection did.

    - `created`: items this import added to the library.
    - `existing`: items the user already had (their own data was merged in).
    - `missing`: references the dictionary no longer has, left out.
    """

    collection: C
    created: int = 0
    existing: int = 0
    missing: list[R] = field(default_factory=list)


@dataclass
class CollectionUpdate(CollectionImport[C, R]):
    """What updating a copy from its source did: as an import, plus
    `removed`, the items the source dropped that left the collection."""

    removed: int = 0


class ImportEntryCollection:
    """Import a shared entry collection (an exported file) as a new collection.

    The rules are the aggregate's (`PracticeEntry.merge_shared`): items the
    user has are reused and the missing ones imported from the dictionary,
    words of someone's own are copied unless the user has a copy of them
    already (same identity), and only what the import creates takes the
    origin's flags. The collection gets a free name. Imported from a public
    collection (`source`), the copy remembers it and its version, its items
    are marked as the source's (`from_source`) and the parts copied into them
    as brought by it: what an update from it relies on. From a file there's
    no source: the copy is never updated, and the parts it copies are pinned
    (`FILE`), so no update from another collection removes them. Doesn't
    commit: the caller owns the transaction, so an invalid item
    imports nothing.
    """

    def __init__(
        self,
        dictionary: DictionaryGateway,
        entries: PracticeEntryRepository,
        collections: EntryCollectionRepository,
    ) -> None:
        self._dictionary = dictionary
        self._entries = entries
        self._collections = collections

    def execute(
        self,
        user_id: UUID,
        shared: SharedEntryCollection,
        source: EntryCollection | None = None,
    ) -> CollectionImport[EntryCollection, int]:
        taken = {c.name for c in self._collections.list_for_user(user_id)}
        collection = self._collections.add(
            EntryCollection(
                id=None,
                user_id=user_id,
                name=free_collection_name(shared.name, taken),
                description=shared.description,
                source_collection_id=source.id if source else None,
                source_version=source.published_version if source else None,
            )
        )
        result: CollectionImport[EntryCollection, int] = CollectionImport(collection)
        brought_by: SourceRef = source.id if source and source.id else FILE
        for _, entry in self.copy_items(user_id, shared.items, brought_by, result):
            self._collections.add_item(collection, entry, from_source=bool(source))
        return result

    def copy_items(
        self,
        user_id: UUID,
        items: Sequence[SharedEntry],
        source: SourceRef | None,
        result: CollectionImport[C, int],
        prune: bool = False,
    ) -> list[tuple[SharedEntry, PracticeEntry]]:
        """Bring each shared word into the user's library, counting in
        `result`: the stored words, with the shared item each came from.
        `prune` (an update) also removes what `source` brought, untouched,
        and no longer has (`PracticeEntry.prune_source`)."""
        own = self._entries.find_own_by_identity(
            {i.identity for i in items if i.identity is not None}, user_id
        )
        copied: list[tuple[SharedEntry, PracticeEntry]] = []
        for item in items:
            entry = (
                self._own_word(user_id, item, own, source, result, prune)
                if item.source_entry_id is None
                else self._dictionary_word(
                    user_id, item, item.source_entry_id, source, result, prune
                )
            )
            if entry is not None:
                copied.append((item, entry))
        return copied

    def _own_word(
        self,
        user_id: UUID,
        item: SharedEntry,
        own: list[PracticeEntry],
        source: SourceRef | None,
        result: CollectionImport[C, int],
        prune: bool,
    ) -> PracticeEntry:
        match = next(
            (
                e
                for e in own
                if item.identity is not None and e.identity == item.identity
            ),
            None,
        )
        if match is None:
            entry = self._entries.add(PracticeEntry.from_shared(user_id, item, source))
            own.append(entry)  # the file may list it twice
            result.created += 1
            return entry
        result.existing += 1
        changed = match.merge_shared(item, created=False, source_collection_id=source)
        if prune and isinstance(source, int):
            changed |= match.prune_source(item, source)
        return self._entries.update(match) if changed else match

    def _dictionary_word(
        self,
        user_id: UUID,
        item: SharedEntry,
        source_entry_id: int,
        source: SourceRef | None,
        result: CollectionImport[C, int],
        prune: bool,
    ) -> PracticeEntry | None:
        existing = self._entries.get_by_source_entry_id(source_entry_id, user_id)
        if existing is None:
            snapshot = self._dictionary.new_practice_entry(source_entry_id, user_id)
            if snapshot is None:
                result.missing.append(source_entry_id)
                return None
            snapshot.merge_shared(item, created=True, source_collection_id=source)
            entry, created = self._entries.add_if_absent(snapshot)
            if created:
                result.created += 1
                return entry
            existing = entry  # imported meanwhile: merge as the user's
        result.existing += 1
        changed = existing.merge_shared(
            item, created=False, source_collection_id=source
        )
        if prune and isinstance(source, int):
            changed |= existing.prune_source(item, source)
        return self._entries.update(existing) if changed else existing


class ImportKanjiCollection:
    """Import a shared kanji collection as a new collection. Same rules as
    `ImportEntryCollection`; every kanji comes from the dictionary."""

    def __init__(
        self,
        dictionary: DictionaryGateway,
        kanji: PracticeKanjiRepository,
        collections: KanjiCollectionRepository,
    ) -> None:
        self._dictionary = dictionary
        self._kanji = kanji
        self._collections = collections

    def execute(
        self,
        user_id: UUID,
        shared: SharedKanjiCollection,
        source: KanjiCollection | None = None,
    ) -> CollectionImport[KanjiCollection, str]:
        taken = {c.name for c in self._collections.list_for_user(user_id)}
        collection = self._collections.add(
            KanjiCollection(
                id=None,
                user_id=user_id,
                name=free_collection_name(shared.name, taken),
                description=shared.description,
                source_collection_id=source.id if source else None,
                source_version=source.published_version if source else None,
            )
        )
        result: CollectionImport[KanjiCollection, str] = CollectionImport(collection)
        brought_by: SourceRef = source.id if source and source.id else FILE
        for _, kanji in self.copy_items(user_id, shared.items, brought_by, result):
            self._collections.add_item(collection, kanji, from_source=bool(source))
        return result

    def copy_items(
        self,
        user_id: UUID,
        items: Sequence[SharedKanji],
        source: SourceRef | None,
        result: CollectionImport[C, str],
        prune: bool = False,
    ) -> list[tuple[SharedKanji, PracticeKanji]]:
        """Bring each shared kanji into the user's library (see
        `ImportEntryCollection.copy_items`)."""
        copied: list[tuple[SharedKanji, PracticeKanji]] = []
        for item in items:
            kanji = self._import(user_id, item, source, result, prune)
            if kanji is not None:
                copied.append((item, kanji))
        return copied

    def _import(
        self,
        user_id: UUID,
        item: SharedKanji,
        source: SourceRef | None,
        result: CollectionImport[C, str],
        prune: bool,
    ) -> PracticeKanji | None:
        existing = self._kanji.get_by_literal(item.literal, user_id)
        if existing is None:
            snapshot = self._dictionary.new_practice_kanji(item.literal, user_id)
            if snapshot is None:
                result.missing.append(item.literal)
                return None
            snapshot.merge_shared(item, created=True, source_collection_id=source)
            kanji, created = self._kanji.add_if_absent(snapshot)
            if created:
                result.created += 1
                return kanji
            existing = kanji
        result.existing += 1
        changed = existing.merge_shared(
            item, created=False, source_collection_id=source
        )
        if prune and isinstance(source, int):
            changed |= existing.prune_source(item, source)
        return self._kanji.update(existing) if changed else existing
