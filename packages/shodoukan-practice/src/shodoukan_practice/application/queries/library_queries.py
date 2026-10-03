"""Read use cases over the user's practice library."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Generic, TypeVar
from uuid import UUID

from ...domain.entities import PracticeEntry, PracticeKanji
from ...domain.repositories import PracticeEntryRepository, PracticeKanjiRepository

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


class ListLibraryEntries:
    """The user's imported entries, most recently imported first.

    Inactive entries are included unless `active` says otherwise, so the
    library page can show and reactivate them.
    """

    def __init__(self, entries: PracticeEntryRepository) -> None:
        self._entries = entries

    def execute(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        active: bool | None = None,
    ) -> LibraryPage[PracticeEntry]:
        return LibraryPage(
            items=self._entries.list_for_user(user_id, limit, offset, active),
            total=self._entries.count_for_user(user_id, active),
            limit=limit,
            offset=offset,
        )


class ListLibraryKanji:
    """The user's imported kanji, like `ListLibraryEntries`."""

    def __init__(self, kanji: PracticeKanjiRepository) -> None:
        self._kanji = kanji

    def execute(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        active: bool | None = None,
    ) -> LibraryPage[PracticeKanji]:
        return LibraryPage(
            items=self._kanji.list_for_user(user_id, limit, offset, active),
            total=self._kanji.count_for_user(user_id, active),
            limit=limit,
            offset=offset,
        )
