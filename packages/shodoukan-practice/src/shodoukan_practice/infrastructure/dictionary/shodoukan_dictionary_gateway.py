from collections.abc import Iterable
from uuid import UUID

from shodoukan import Dictionary

from ...domain.entities import PracticeEntry, PracticeKanji, ReferenceKanji
from ...domain.gateways import (
    DictionaryEntry,
    DictionaryEntryPage,
    DictionaryGateway,
    DictionaryKanji,
    DictionaryKanjiStrokes,
    DictionarySearchResult,
)
from .shodoukan_mapper import (
    shodoukan_entry_page_to_dictionary,
    shodoukan_entry_to_dictionary,
    shodoukan_entry_to_practice,
    shodoukan_kanji_strokes_to_dictionary,
    shodoukan_kanji_to_dictionary,
    shodoukan_kanji_to_practice,
    shodoukan_search_to_dictionary,
    shodoukan_strokes_to_reference,
)


class ShodoukanDictionaryGateway(DictionaryGateway):
    """Reads the dictionary in-process through the `shodoukan` library."""

    def __init__(self, dictionary: Dictionary) -> None:
        self._dictionary = dictionary

    def new_practice_entry(
        self, source_entry_id: int, user_id: UUID
    ) -> PracticeEntry | None:
        entry = self._dictionary.get_entry(source_entry_id)
        return shodoukan_entry_to_practice(entry, user_id) if entry else None

    def new_practice_kanji(self, literal: str, user_id: UUID) -> PracticeKanji | None:
        kanji = self._dictionary.get_kanji(literal)
        return shodoukan_kanji_to_practice(kanji, user_id) if kanji else None

    def search(
        self, query: str, lang: str, limit: int, offset: int
    ) -> DictionarySearchResult:
        result = self._dictionary.search(query, lang=lang, limit=limit, offset=offset)
        return shodoukan_search_to_dictionary(result)

    def get_entry(self, entry_id: int) -> DictionaryEntry | None:
        entry = self._dictionary.get_entry(entry_id)
        return shodoukan_entry_to_dictionary(entry) if entry else None

    def get_kanji(self, literal: str) -> DictionaryKanji | None:
        kanji = self._dictionary.get_kanji(literal)
        return shodoukan_kanji_to_dictionary(kanji) if kanji else None

    def kanji_strokes(self, literal: str) -> DictionaryKanjiStrokes | None:
        strokes = self._dictionary.get_kanji_strokes(literal)
        return shodoukan_kanji_strokes_to_dictionary(strokes) if strokes else None

    def literals_with_strokes(self, literals: Iterable[str]) -> frozenset[str]:
        return frozenset(self._dictionary.literals_with_strokes(literals))

    def stroke_references(self, literals: Iterable[str]) -> dict[str, ReferenceKanji]:
        references = {}
        for literal in dict.fromkeys(literals):
            strokes = self._dictionary.get_kanji_strokes(literal)
            if strokes and strokes.strokes:
                references[literal] = shodoukan_strokes_to_reference(strokes)
        return references

    def entries_for_kanji(
        self, literal: str, limit: int, offset: int
    ) -> DictionaryEntryPage:
        page = self._dictionary.get_entries_for_kanji(
            literal, limit=limit, offset=offset
        )
        return shodoukan_entry_page_to_dictionary(page)

    def kanji_for_entry(self, entry_id: int) -> list[DictionaryKanji]:
        return [
            shodoukan_kanji_to_dictionary(k)
            for k in self._dictionary.get_kanji_for_entry_related(entry_id)
        ]
