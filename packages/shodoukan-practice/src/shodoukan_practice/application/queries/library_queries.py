"""Read use cases over the user's practice library."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Generic, TypeVar
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

T = TypeVar("T")


@dataclass(frozen=True)
class LibraryPage(Generic[T]):
    """A page of the user's library, and how many items there are in total."""

    items: list[T]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class ImportStatus:
    """Which of the asked-about dictionary items the user has imported.

    Only imported items appear, mapped to their practice ids.
    """

    entries: dict[int, int]  # source_entry_id -> practice entry id
    kanji: dict[str, int]  # literal -> practice kanji id


class GetImportStatus:
    """Import status of a set of dictionary items, e.g. a page of search results.

    The dictionary search itself stays in shodoukan-api; the frontend asks
    this in parallel to enable or disable each Import button.
    """

    def __init__(
        self, entries: PracticeEntryRepository, kanji: PracticeKanjiRepository
    ) -> None:
        self._entries = entries
        self._kanji = kanji

    def execute(
        self, user_id: UUID, source_entry_ids: Iterable[int], literals: Iterable[str]
    ) -> ImportStatus:
        entry_ids = list(dict.fromkeys(source_entry_ids))
        kanji_literals = list(dict.fromkeys(literals))
        return ImportStatus(
            entries=self._entries.practice_ids_by_source_entry_id(entry_ids, user_id)
            if entry_ids
            else {},
            kanji=self._kanji.practice_ids_by_literal(kanji_literals, user_id)
            if kanji_literals
            else {},
        )


class GetLibraryEntry:
    """One entry of the user's library; `EntityNotFoundError` if it isn't theirs."""

    def __init__(self, entries: PracticeEntryRepository) -> None:
        self._entries = entries

    def execute(self, user_id: UUID, entry_id: int) -> PracticeEntry:
        entry = self._entries.get(entry_id, user_id)
        if entry is None:
            raise EntityNotFoundError(f"entry {entry_id} not found")
        return entry


class GetLibraryKanji:
    """One kanji of the user's library; `EntityNotFoundError` if it isn't theirs."""

    def __init__(self, kanji: PracticeKanjiRepository) -> None:
        self._kanji = kanji

    def execute(self, user_id: UUID, kanji_id: int) -> PracticeKanji:
        kanji = self._kanji.get(kanji_id, user_id)
        if kanji is None:
            raise EntityNotFoundError(f"kanji {kanji_id} not found")
        return kanji


class ListCollectionsOfEntry:
    """The collections (tags) an entry of the user's library is in, by name."""

    def __init__(
        self, entries: PracticeEntryRepository, collections: EntryCollectionRepository
    ) -> None:
        self._get = GetLibraryEntry(entries)
        self._collections = collections

    def execute(self, user_id: UUID, entry_id: int) -> list[EntryCollection]:
        return self._collections.list_for_item(self._get.execute(user_id, entry_id))


class ListCollectionsOfKanji:
    """The collections (tags) a kanji of the user's library is in, by name."""

    def __init__(
        self, kanji: PracticeKanjiRepository, collections: KanjiCollectionRepository
    ) -> None:
        self._get = GetLibraryKanji(kanji)
        self._collections = collections

    def execute(self, user_id: UUID, kanji_id: int) -> list[KanjiCollection]:
        return self._collections.list_for_item(self._get.execute(user_id, kanji_id))
