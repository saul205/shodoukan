"""Read use cases over public collections: searching them, one's summary, and
a preview of its published version.

Anyone signed in can read a public collection; a private one is "not found"
to everyone, its owner included (they read it as their own collection).
"""

from dataclasses import dataclass
from typing import Generic, TypeVar
from uuid import UUID

from ...domain.entities import (
    EntryCollection,
    KanjiCollection,
    PracticeEntry,
    PracticeKanji,
    PracticeSentence,
)
from ...domain.exceptions import EntityNotFoundError
from ...domain.gateways import DictionaryGateway
from ...domain.repositories import (
    EntryCollectionRepository,
    KanjiCollectionRepository,
)
from ...domain.searches import (
    PublicCollectionSearch,
    PublicCollectionSummary,
    PublicOwner,
    PublicSort,
)
from ...domain.services import preview_sentences
from .library_queries import LibraryPage

C = TypeVar("C", EntryCollection, KanjiCollection)


@dataclass(frozen=True)
class PublicCollectionPage(Generic[C]):
    """A page of public collections, and how many match in total."""

    items: list[PublicCollectionSummary[C]]
    total: int
    limit: int
    offset: int


def build_public_search(
    text: str | None, owner: PublicOwner, sort: PublicSort
) -> PublicCollectionSearch:
    """The search for what the user typed: trimmed, lower-cased, or none."""
    text = (text or "").strip().lower() or None
    return PublicCollectionSearch(text=text, owner=owner, sort=sort)


class SearchPublicEntryCollections:
    """Public entry collections matching the search, a page at a time."""

    def __init__(self, collections: EntryCollectionRepository) -> None:
        self._collections = collections

    def execute(
        self,
        viewer_id: UUID,
        text: str | None = None,
        owner: PublicOwner = "all",
        sort: PublicSort = "popular",
        limit: int = 20,
        offset: int = 0,
    ) -> PublicCollectionPage[EntryCollection]:
        search = build_public_search(text, owner, sort)
        return PublicCollectionPage(
            items=self._collections.find_public(search, viewer_id, limit, offset),
            total=self._collections.count_public(search, viewer_id),
            limit=limit,
            offset=offset,
        )


class SearchPublicKanjiCollections:
    """Public kanji collections matching the search, a page at a time."""

    def __init__(self, collections: KanjiCollectionRepository) -> None:
        self._collections = collections

    def execute(
        self,
        viewer_id: UUID,
        text: str | None = None,
        owner: PublicOwner = "all",
        sort: PublicSort = "popular",
        limit: int = 20,
        offset: int = 0,
    ) -> PublicCollectionPage[KanjiCollection]:
        search = build_public_search(text, owner, sort)
        return PublicCollectionPage(
            items=self._collections.find_public(search, viewer_id, limit, offset),
            total=self._collections.count_public(search, viewer_id),
            limit=limit,
            offset=offset,
        )


class GetPublicEntryCollection:
    """A public entry collection with its owner and counts."""

    def __init__(self, collections: EntryCollectionRepository) -> None:
        self._collections = collections

    def execute(
        self, viewer_id: UUID, collection_id: int
    ) -> PublicCollectionSummary[EntryCollection]:
        collection = self._collections.get_public(collection_id)
        if collection is None:
            raise EntityNotFoundError(f"public collection {collection_id} not found")
        return self._collections.public_summary(collection, viewer_id)


class GetPublicKanjiCollection:
    """A public kanji collection with its owner and counts."""

    def __init__(self, collections: KanjiCollectionRepository) -> None:
        self._collections = collections

    def execute(
        self, viewer_id: UUID, collection_id: int
    ) -> PublicCollectionSummary[KanjiCollection]:
        collection = self._collections.get_public(collection_id)
        if collection is None:
            raise EntityNotFoundError(f"public collection {collection_id} not found")
        return self._collections.public_summary(collection, viewer_id)


@dataclass(frozen=True)
class EntryPreview:
    """A word of a public collection as importing it would give it, with
    the sentences it would bring (`preview_sentences`)."""

    entry: PracticeEntry
    sentences: list[PracticeSentence]


class PreviewPublicEntryCollection:
    """A page of a public entry collection's published version, each word as
    the viewer would get it by importing it into an empty library: a fresh
    dictionary snapshot with the owner's data merged in, and its sentences.
    Nothing is stored, so they have no ids. A word the dictionary no longer
    has is left out of its page (`total` still counts it)."""

    def __init__(
        self,
        collections: EntryCollectionRepository,
        dictionary: DictionaryGateway,
    ) -> None:
        self._collections = collections
        self._dictionary = dictionary

    def execute(
        self, viewer_id: UUID, collection_id: int, limit: int = 20, offset: int = 0
    ) -> LibraryPage[EntryPreview]:
        collection = self._collections.get_public(collection_id)
        shared = self._collections.get_publication(collection) if collection else None
        if shared is None:
            raise EntityNotFoundError(f"public collection {collection_id} not found")
        previews: list[EntryPreview] = []
        for item in shared.items[offset : offset + limit]:
            if item.source_entry_id is None:
                entry: PracticeEntry | None = PracticeEntry.from_shared(viewer_id, item)
            else:
                entry = self._dictionary.new_practice_entry(
                    item.source_entry_id, viewer_id
                )
                if entry is not None:
                    entry.merge_shared(item, created=True)
            if entry is not None:
                previews.append(EntryPreview(entry, preview_sentences(item, viewer_id)))
        return LibraryPage(previews, len(shared.items), limit, offset)


class PreviewPublicKanjiCollection:
    """A page of a public kanji collection's published version, as the viewer
    would get it. Same rules as `PreviewPublicEntryCollection`."""

    def __init__(
        self,
        collections: KanjiCollectionRepository,
        dictionary: DictionaryGateway,
    ) -> None:
        self._collections = collections
        self._dictionary = dictionary

    def execute(
        self, viewer_id: UUID, collection_id: int, limit: int = 20, offset: int = 0
    ) -> LibraryPage[PracticeKanji]:
        collection = self._collections.get_public(collection_id)
        shared = self._collections.get_publication(collection) if collection else None
        if shared is None:
            raise EntityNotFoundError(f"public collection {collection_id} not found")
        kanji: list[PracticeKanji] = []
        for item in shared.items[offset : offset + limit]:
            snapshot = self._dictionary.new_practice_kanji(item.literal, viewer_id)
            if snapshot is not None:
                snapshot.merge_shared(item, created=True)
                kanji.append(snapshot)
        return LibraryPage(kanji, len(shared.items), limit, offset)


class LatestEntrySourceVersions:
    """`{collection id: its source's published version}` for the user's entry
    copies whose source is still public: a copy behind it can be updated."""

    def __init__(self, collections: EntryCollectionRepository) -> None:
        self._collections = collections

    def execute(self, user_id: UUID) -> dict[int, int]:
        return self._collections.latest_source_versions(user_id)


class LatestKanjiSourceVersions:
    """The same for the user's kanji copies."""

    def __init__(self, collections: KanjiCollectionRepository) -> None:
        self._collections = collections

    def execute(self, user_id: UUID) -> dict[int, int]:
        return self._collections.latest_source_versions(user_id)
