"""Read use cases over the user's practice library."""

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories import PracticeEntryRepository, PracticeKanjiRepository


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
