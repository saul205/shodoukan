"""Use cases that add items to a user's practice library: dictionary items,
and words of the user's own."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar
from uuid import UUID

from ...domain.entities import PracticeEntry, PracticeKanji
from ...domain.exceptions import DictionaryItemNotFoundError
from ...domain.gateways import DictionaryGateway
from ...domain.repositories import (
    EntryCollectionRepository,
    KanjiCollectionRepository,
    PracticeEntryRepository,
    PracticeKanjiRepository,
)
from .collection_lookups import entry_collection, kanji_collection

T = TypeVar("T")


@dataclass(frozen=True)
class ImportResult(Generic[T]):
    """The item in the user's library, and whether this call added it."""

    item: T
    created: bool


class ImportEntry:
    """Copy a dictionary entry into the user's library, and into collections.

    Idempotent: if the user already has the entry, that copy is returned
    unchanged (it's still put in the given collections). The collections are
    checked first, so an unknown one (`EntityNotFoundError`) imports nothing.
    Doesn't commit; the caller owns the transaction.
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
        source_entry_id: int,
        collection_ids: Sequence[int] = (),
    ) -> ImportResult[PracticeEntry]:
        targets = [
            entry_collection(self._collections, collection_id, user_id)
            for collection_id in dict.fromkeys(collection_ids)
        ]
        result = self._import(user_id, source_entry_id)
        for collection in targets:
            self._collections.add_item(collection, result.item)
        return result

    def _import(
        self, user_id: UUID, source_entry_id: int
    ) -> ImportResult[PracticeEntry]:
        existing = self._entries.get_by_source_entry_id(source_entry_id, user_id)
        if existing is not None:
            return ImportResult(existing, created=False)

        snapshot = self._dictionary.new_practice_entry(source_entry_id, user_id)
        if snapshot is None:
            raise DictionaryItemNotFoundError(f"entry {source_entry_id} not found")
        item, created = self._entries.add_if_absent(snapshot)
        return ImportResult(item, created)


class CreateOwnEntry:
    """Create a word of the user's own (not in the dictionary), and put it in
    collections.

    The collections are checked first, so an unknown one
    (`EntityNotFoundError`) creates nothing. Not idempotent: the user can
    have any number of words of their own, even alike. Doesn't commit.
    """

    def __init__(
        self,
        entries: PracticeEntryRepository,
        collections: EntryCollectionRepository,
    ) -> None:
        self._entries = entries
        self._collections = collections

    def execute(
        self,
        user_id: UUID,
        spellings: Sequence[str],
        readings: Sequence[str],
        meaning: str,
        lang: str,
        collection_ids: Sequence[int] = (),
    ) -> PracticeEntry:
        targets = [
            entry_collection(self._collections, collection_id, user_id)
            for collection_id in dict.fromkeys(collection_ids)
        ]
        entry = self._entries.add(
            PracticeEntry.create_own(user_id, spellings, readings, meaning, lang)
        )
        for collection in targets:
            self._collections.add_item(collection, entry)
        return entry


class ImportKanji:
    """Copy a dictionary kanji into the user's library, and into collections.

    Same rules as `ImportEntry`. Doesn't commit.
    """

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
        self, user_id: UUID, literal: str, collection_ids: Sequence[int] = ()
    ) -> ImportResult[PracticeKanji]:
        targets = [
            kanji_collection(self._collections, collection_id, user_id)
            for collection_id in dict.fromkeys(collection_ids)
        ]
        result = self._import(user_id, literal)
        for collection in targets:
            self._collections.add_item(collection, result.item)
        return result

    def _import(self, user_id: UUID, literal: str) -> ImportResult[PracticeKanji]:
        existing = self._kanji.get_by_literal(literal, user_id)
        if existing is not None:
            return ImportResult(existing, created=False)

        snapshot = self._dictionary.new_practice_kanji(literal, user_id)
        if snapshot is None:
            raise DictionaryItemNotFoundError(f"kanji {literal!r} not found")
        item, created = self._kanji.add_if_absent(snapshot)
        return ImportResult(item, created)
