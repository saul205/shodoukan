"""Read use cases over the shodoukan dictionary."""

from ...domain.gateways import DictionaryGateway, DictionarySearchResult


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
