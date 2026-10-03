"""Searching the library: the use cases behind every list of library items.

The library page, a collection and the "add to collection" picker all run
the same search with a different scope. This module does what they share
once: normalizing the query, loading the collection (and checking it's the
user's), the active rule and paging. The item repositories run the search.
"""

from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from ...domain.entities import (
    Collection,
    EntryCollection,
    KanjiCollection,
    PracticeEntry,
    PracticeKanji,
)
from ...domain.gateways import KanaGateway
from ...domain.repositories import (
    EntryCollectionRepository,
    KanjiCollectionRepository,
    PracticeEntryRepository,
    PracticeKanjiRepository,
)
from ...domain.searches import (
    InCollection,
    LibrarySearch,
    NotInCollection,
    SearchScope,
    WholeLibrary,
)
from .collection_queries import GetEntryCollection, GetKanjiCollection
from .library_queries import LibraryPage

C = TypeVar("C", bound=Collection)


def build_search(
    text: str | None,
    meaning_lang: str | None,
    active: bool | None,
    kana: KanaGateway,
) -> LibrarySearch:
    """The search for what the user typed: trimmed, lower-cased, with its kana.

    Blank text searches nothing, so the scope is listed as is.
    """
    normalized = (text or "").strip().lower()
    return LibrarySearch(
        text=normalized or None,
        kana=kana.kana_forms(normalized) if normalized else None,
        meaning_lang=meaning_lang or None,
        active=active,
    )


def resolve_scope(
    get_collection: Callable[[int], C],
    in_collection: int | None,
    not_in_collection: int | None,
) -> SearchScope[C]:
    """The scope for the given collection ids, loading the collection.

    `get_collection` raises `EntityNotFoundError` if it isn't the user's.
    """
    if in_collection is not None and not_in_collection is not None:
        raise ValueError("search in a collection or outside one, not both")
    if in_collection is not None:
        return InCollection(get_collection(in_collection))
    if not_in_collection is not None:
        return NotInCollection(get_collection(not_in_collection))
    return WholeLibrary()


def _active_in(scope: SearchScope[C], active: bool | None) -> bool | None:
    # A collection shows its active items only: inactive ones aren't practised.
    return True if isinstance(scope, InCollection) else active


class SearchEntries:
    """A page of the user's entries matching what they typed, within a scope.

    - Whole library: inactive entries too, unless `active` says otherwise.
    - `in_collection`: the collection's active entries.
    - `not_in_collection`: the library minus the collection's entries.

    Best match first; without text, the scope's own order.
    """

    def __init__(
        self,
        entries: PracticeEntryRepository,
        collections: EntryCollectionRepository,
        kana: KanaGateway,
    ) -> None:
        self._entries = entries
        self._get_collection = GetEntryCollection(collections)
        self._kana = kana

    def execute(
        self,
        user_id: UUID,
        text: str | None = None,
        meaning_lang: str | None = None,
        active: bool | None = None,
        in_collection: int | None = None,
        not_in_collection: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> LibraryPage[PracticeEntry]:
        scope: SearchScope[EntryCollection] = resolve_scope(
            lambda collection_id: self._get_collection.execute(user_id, collection_id),
            in_collection,
            not_in_collection,
        )
        search = build_search(text, meaning_lang, _active_in(scope, active), self._kana)
        return LibraryPage(
            items=self._entries.find(user_id, search, scope, limit, offset),
            total=self._entries.count(user_id, search, scope),
            limit=limit,
            offset=offset,
        )


class SearchKanji:
    """A page of the user's kanji matching what they typed, within a scope.

    Same scopes and order as `SearchEntries`.
    """

    def __init__(
        self,
        kanji: PracticeKanjiRepository,
        collections: KanjiCollectionRepository,
        kana: KanaGateway,
    ) -> None:
        self._kanji = kanji
        self._get_collection = GetKanjiCollection(collections)
        self._kana = kana

    def execute(
        self,
        user_id: UUID,
        text: str | None = None,
        meaning_lang: str | None = None,
        active: bool | None = None,
        in_collection: int | None = None,
        not_in_collection: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> LibraryPage[PracticeKanji]:
        scope: SearchScope[KanjiCollection] = resolve_scope(
            lambda collection_id: self._get_collection.execute(user_id, collection_id),
            in_collection,
            not_in_collection,
        )
        search = build_search(text, meaning_lang, _active_in(scope, active), self._kana)
        return LibraryPage(
            items=self._kanji.find(user_id, search, scope, limit, offset),
            total=self._kanji.count(user_id, search, scope),
            limit=limit,
            offset=offset,
        )
