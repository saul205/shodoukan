from shodoukan import Dictionary

from ...domain.entities import PracticeEntry, PracticeKanji
from ...domain.gateways import DictionaryGateway
from .shodoukan_mapper import shodoukan_entry_to_practice, shodoukan_kanji_to_practice


class ShodoukanDictionaryGateway(DictionaryGateway):
    """Reads the dictionary in-process through the `shodoukan` library."""

    def __init__(self, dictionary: Dictionary) -> None:
        self._dictionary = dictionary

    def new_practice_entry(
        self, source_entry_id: int, user_id: int
    ) -> PracticeEntry | None:
        entry = self._dictionary.get_entry(source_entry_id)
        return shodoukan_entry_to_practice(entry, user_id) if entry else None

    def new_practice_kanji(self, literal: str, user_id: int) -> PracticeKanji | None:
        kanji = self._dictionary.get_kanji(literal)
        return shodoukan_kanji_to_practice(kanji, user_id) if kanji else None
