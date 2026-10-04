"""Port for turning what the user types into kana.

Searching the library by reading needs the kana forms of a query: romaji is
converted (`taberu` → `たべる`) and both scripts are wanted, since readings
are stored in hiragana (kun, most words) or katakana (on, loanwords).
"""

from typing import NamedTuple, Protocol


class KanaForms(NamedTuple):
    hiragana: str
    katakana: str


class KanaGateway(Protocol):
    def kana_forms(self, text: str) -> KanaForms | None:
        """`text` in hiragana and katakana, if it's romaji or kana.

        `None` when it can't be read as kana (English words with letters that
        aren't romaji, kanji, digits, ...).
        """
        ...
