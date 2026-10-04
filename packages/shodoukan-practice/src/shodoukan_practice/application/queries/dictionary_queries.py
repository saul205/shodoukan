"""Read use cases over the shodoukan dictionary.

All public: the dictionary is the same for every user.
"""

from ...domain.exceptions import DictionaryItemNotFoundError
from ...domain.gateways import (
    DictionaryEntry,
    DictionaryEntryPage,
    DictionaryGateway,
    DictionaryKanji,
    DictionarySearchResult,
)


class SearchDictionary:
    """Search the dictionary by kanji, kana, Hepburn romaji or meaning.

    Public: results are the same for every user. Whether each result is in
    the user's library is a separate query (`GetImportStatus`).
    """

    def __init__(self, dictionary: DictionaryGateway) -> None:
        self._dictionary = dictionary

    def execute(
        self, query: str, lang: str = "en", limit: int = 20, offset: int = 0
    ) -> DictionarySearchResult:
        return self._dictionary.search(query, lang=lang, limit=limit, offset=offset)


class GetDictionaryEntry:
    """One dictionary entry; `DictionaryItemNotFoundError` if there's none."""

    def __init__(self, dictionary: DictionaryGateway) -> None:
        self._dictionary = dictionary

    def execute(self, entry_id: int) -> DictionaryEntry:
        entry = self._dictionary.get_entry(entry_id)
        if entry is None:
            raise DictionaryItemNotFoundError(f"entry {entry_id} not found")
        return entry


class GetDictionaryKanji:
    """One dictionary kanji; `DictionaryItemNotFoundError` if there's none."""

    def __init__(self, dictionary: DictionaryGateway) -> None:
        self._dictionary = dictionary

    def execute(self, literal: str) -> DictionaryKanji:
        kanji = self._dictionary.get_kanji(literal)
        if kanji is None:
            raise DictionaryItemNotFoundError(f"kanji {literal!r} not found")
        return kanji


class ListEntriesForKanji:
    """A page of the words written with a kanji, for its detail page.

    `DictionaryItemNotFoundError` if the kanji isn't in the dictionary, so a
    typo isn't mistaken for a kanji no word uses.
    """

    def __init__(self, dictionary: DictionaryGateway) -> None:
        self._dictionary = dictionary

    def execute(
        self, literal: str, limit: int = 20, offset: int = 0
    ) -> DictionaryEntryPage:
        GetDictionaryKanji(self._dictionary).execute(literal)
        return self._dictionary.entries_for_kanji(literal, limit, offset)


class ListKanjiForEntry:
    """The kanji an entry is written with, for its detail page."""

    def __init__(self, dictionary: DictionaryGateway) -> None:
        self._dictionary = dictionary

    def execute(self, entry_id: int) -> list[DictionaryKanji]:
        GetDictionaryEntry(self._dictionary).execute(entry_id)
        return self._dictionary.kanji_for_entry(entry_id)
