"""Use cases that add dictionary items to a user's practice library."""

from dataclasses import dataclass
from typing import Generic, TypeVar

from ...domain.entities import PracticeEntry, PracticeKanji
from ...domain.exceptions import DictionaryItemNotFoundError
from ...domain.gateways import DictionaryGateway
from ...domain.repositories import PracticeEntryRepository, PracticeKanjiRepository

T = TypeVar("T")


@dataclass(frozen=True)
class ImportResult(Generic[T]):
    """The item in the user's library, and whether this call added it."""

    item: T
    created: bool


class ImportEntry:
    """Copy a dictionary entry into the user's library.

    Idempotent: if the user already has the entry, that copy is returned and
    nothing changes. Doesn't commit; the caller owns the transaction.
    """

    def __init__(
        self, dictionary: DictionaryGateway, entries: PracticeEntryRepository
    ) -> None:
        self._dictionary = dictionary
        self._entries = entries

    def execute(
        self, user_id: int, source_entry_id: int
    ) -> ImportResult[PracticeEntry]:
        existing = self._entries.get_by_source_entry_id(source_entry_id, user_id)
        if existing is not None:
            return ImportResult(existing, created=False)

        snapshot = self._dictionary.new_practice_entry(source_entry_id, user_id)
        if snapshot is None:
            raise DictionaryItemNotFoundError(f"entry {source_entry_id} not found")
        item, created = self._entries.add_if_absent(snapshot)
        return ImportResult(item, created)


class ImportKanji:
    """Copy a dictionary kanji into the user's library.

    Idempotent, like `ImportEntry`. Doesn't commit.
    """

    def __init__(
        self, dictionary: DictionaryGateway, kanji: PracticeKanjiRepository
    ) -> None:
        self._dictionary = dictionary
        self._kanji = kanji

    def execute(self, user_id: int, literal: str) -> ImportResult[PracticeKanji]:
        existing = self._kanji.get_by_literal(literal, user_id)
        if existing is not None:
            return ImportResult(existing, created=False)

        snapshot = self._dictionary.new_practice_kanji(literal, user_id)
        if snapshot is None:
            raise DictionaryItemNotFoundError(f"kanji {literal!r} not found")
        item, created = self._kanji.add_if_absent(snapshot)
        return ImportResult(item, created)
