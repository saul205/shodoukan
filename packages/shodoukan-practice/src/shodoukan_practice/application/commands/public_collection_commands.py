"""Use cases that share collections: publishing them, importing a public one
into the user's library, and updating such a copy from its source.

Entry and kanji collections get their own use cases, like the rest of the
collection use cases. None of them commit; the caller owns the transaction.
"""

from uuid import UUID

from ...domain.entities import EntryCollection, KanjiCollection
from ...domain.exceptions import EntityNotFoundError
from ...domain.gateways import DictionaryGateway
from ...domain.repositories import (
    EntryCollectionRepository,
    KanjiCollectionRepository,
    PracticeEntryRepository,
    PracticeKanjiRepository,
    PracticeSentenceRepository,
)
from ..queries.collection_queries import ExportEntryCollection, ExportKanjiCollection
from .collection_commands import (
    CollectionImport,
    CollectionUpdate,
    ImportEntryCollection,
    ImportKanjiCollection,
)
from .collection_lookups import entry_collection, kanji_collection

# --- Publish ---


class PublishEntryCollection:
    """Publish a new version of one of the user's entry collections.

    Its snapshot is the export of its active items, with the user's notes
    only if `include_notes`; it replaces the previous version. Raises
    `EntityNotFoundError` for a collection the user doesn't have, and
    `ValidationError` for one with more active items than an import takes.
    """

    def __init__(
        self,
        collections: EntryCollectionRepository,
        entries: PracticeEntryRepository,
    ) -> None:
        self._collections = collections
        self._entries = entries

    def execute(
        self, user_id: UUID, collection_id: int, include_notes: bool
    ) -> EntryCollection:
        shared = ExportEntryCollection(self._collections, self._entries).execute(
            user_id, collection_id, active_only=True, include_notes=include_notes
        )
        collection = entry_collection(self._collections, collection_id, user_id)
        collection.publish()
        collection = self._collections.update(collection)
        self._collections.save_publication(collection, shared, include_notes)
        return collection


class PublishKanjiCollection:
    """Publish a new version of one of the user's kanji collections. Same
    rules as `PublishEntryCollection`."""

    def __init__(
        self,
        collections: KanjiCollectionRepository,
        kanji: PracticeKanjiRepository,
    ) -> None:
        self._collections = collections
        self._kanji = kanji

    def execute(
        self, user_id: UUID, collection_id: int, include_notes: bool
    ) -> KanjiCollection:
        shared = ExportKanjiCollection(self._collections, self._kanji).execute(
            user_id, collection_id, active_only=True, include_notes=include_notes
        )
        collection = kanji_collection(self._collections, collection_id, user_id)
        collection.publish()
        collection = self._collections.update(collection)
        self._collections.save_publication(collection, shared, include_notes)
        return collection


class UnpublishEntryCollection:
    """Make one of the user's entry collections private again. Its last
    version, downloads and the rest are kept for publishing it again."""

    def __init__(self, collections: EntryCollectionRepository) -> None:
        self._collections = collections

    def execute(self, user_id: UUID, collection_id: int) -> EntryCollection:
        collection = entry_collection(self._collections, collection_id, user_id)
        collection.unpublish()
        return self._collections.update(collection)


class UnpublishKanjiCollection:
    """Make one of the user's kanji collections private again."""

    def __init__(self, collections: KanjiCollectionRepository) -> None:
        self._collections = collections

    def execute(self, user_id: UUID, collection_id: int) -> KanjiCollection:
        collection = kanji_collection(self._collections, collection_id, user_id)
        collection.unpublish()
        return self._collections.update(collection)


# --- Import ---


class ImportPublicEntryCollection:
    """Import the latest version of a public entry collection, as a new
    collection of the user's (`ImportEntryCollection`).

    The copy remembers the version, and the download is recorded unless the
    user is its owner. A private or missing collection is `EntityNotFoundError`.
    """

    def __init__(
        self,
        dictionary: DictionaryGateway,
        entries: PracticeEntryRepository,
        collections: EntryCollectionRepository,
        sentences: PracticeSentenceRepository,
    ) -> None:
        self._dictionary = dictionary
        self._entries = entries
        self._collections = collections
        self._sentences = sentences

    def execute(
        self, user_id: UUID, collection_id: int
    ) -> CollectionImport[EntryCollection, int]:
        source = self._collections.get_public(collection_id)
        shared = self._collections.get_publication(source) if source else None
        if source is None or shared is None:
            raise EntityNotFoundError(f"public collection {collection_id} not found")
        version = source.published_version
        result = ImportEntryCollection(
            self._dictionary, self._entries, self._collections, self._sentences
        ).execute(user_id, shared, source=source)
        if user_id != source.user_id:
            self._collections.record_download(source, user_id, version)
        return result


class ImportPublicKanjiCollection:
    """Import the latest version of a public kanji collection. Same rules as
    `ImportPublicEntryCollection`."""

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
        self, user_id: UUID, collection_id: int
    ) -> CollectionImport[KanjiCollection, str]:
        source = self._collections.get_public(collection_id)
        shared = self._collections.get_publication(source) if source else None
        if source is None or shared is None:
            raise EntityNotFoundError(f"public collection {collection_id} not found")
        version = source.published_version
        result = ImportKanjiCollection(
            self._dictionary, self._kanji, self._collections
        ).execute(user_id, shared, source=source)
        if user_id != source.user_id:
            self._collections.record_download(source, user_id, version)
        return result


# --- Update from the source ---


class UpdateEntryCollectionFromSource:
    """Bring one of the user's copies up to its source's latest version.

    One rule, item by item: what came from the source and is untouched
    follows it, what the user touched or added is theirs. New items and parts
    are imported as an import does; the source's dropped items leave the
    collection (never the library) and its dropped parts, if untouched, leave
    the word (`PracticeEntry.prune_source`). What the user took out of the
    copy (`dismiss_item`) or deleted from a word (`dismissed_parts`) isn't
    brought back. The user's download row takes the new version (it isn't
    another download). Nothing changes if the copy is up to date. A source that's
    gone or private is `EntityNotFoundError`. Doesn't commit.
    """

    def __init__(
        self,
        dictionary: DictionaryGateway,
        entries: PracticeEntryRepository,
        collections: EntryCollectionRepository,
        sentences: PracticeSentenceRepository,
    ) -> None:
        self._dictionary = dictionary
        self._entries = entries
        self._collections = collections
        self._sentences = sentences

    def execute(
        self, user_id: UUID, collection_id: int
    ) -> CollectionUpdate[EntryCollection, int]:
        copy = entry_collection(self._collections, collection_id, user_id)
        source_id = copy.source_collection_id
        source = self._collections.get_public(source_id) if source_id else None
        shared = self._collections.get_publication(source) if source else None
        if source is None or shared is None:
            raise EntityNotFoundError(
                f"the source of collection {collection_id} is gone"
            )
        result: CollectionUpdate[EntryCollection, int] = CollectionUpdate(copy)
        version = source.published_version
        if copy.source_version is not None and version <= copy.source_version:
            return result

        dismissed = self._collections.dismissed_items(copy)
        items = [item for item in shared.items if item.key not in dismissed]
        importer = ImportEntryCollection(
            self._dictionary, self._entries, self._collections, self._sentences
        )
        for _, entry in importer.copy_items(
            user_id, items, source.id, result, prune=True
        ):
            self._collections.add_item(copy, entry, from_source=True)
        keys = {item.key for item in shared.items}
        followed = self._collections.source_item_ids(copy)
        for entry in self._entries.get_many(followed, user_id):
            if entry.shared_key not in keys:
                self._collections.remove_item(copy, entry)
                result.removed += 1
        copy.follow_source(version)
        result.collection = self._collections.update(copy)
        # The user now has this version: what the public listing shows them.
        if user_id != source.user_id:
            self._collections.record_download(source, user_id, version)
        return result


class UpdateKanjiCollectionFromSource:
    """Bring one of the user's kanji copies up to its source's latest
    version. Same rules as `UpdateEntryCollectionFromSource`."""

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
        self, user_id: UUID, collection_id: int
    ) -> CollectionUpdate[KanjiCollection, str]:
        copy = kanji_collection(self._collections, collection_id, user_id)
        source_id = copy.source_collection_id
        source = self._collections.get_public(source_id) if source_id else None
        shared = self._collections.get_publication(source) if source else None
        if source is None or shared is None:
            raise EntityNotFoundError(
                f"the source of collection {collection_id} is gone"
            )
        result: CollectionUpdate[KanjiCollection, str] = CollectionUpdate(copy)
        version = source.published_version
        if copy.source_version is not None and version <= copy.source_version:
            return result

        dismissed = self._collections.dismissed_items(copy)
        items = [item for item in shared.items if item.key not in dismissed]
        importer = ImportKanjiCollection(
            self._dictionary, self._kanji, self._collections
        )
        for _, kanji in importer.copy_items(
            user_id, items, source.id, result, prune=True
        ):
            self._collections.add_item(copy, kanji, from_source=True)
        keys = {item.key for item in shared.items}
        followed = self._collections.source_item_ids(copy)
        for kanji in self._kanji.get_many(followed, user_id):
            if kanji.shared_key not in keys:
                self._collections.remove_item(copy, kanji)
                result.removed += 1
        copy.follow_source(version)
        result.collection = self._collections.update(copy)
        # The user now has this version: what the public listing shows them.
        if user_id != source.user_id:
            self._collections.record_download(source, user_id, version)
        return result
