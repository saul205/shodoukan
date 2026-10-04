"""The shodoukan dictionary and its kana tools, used in-process via `shodoukan`."""

from .shodoukan_dictionary_gateway import ShodoukanDictionaryGateway
from .shodoukan_kana_gateway import ShodoukanKanaGateway
from .shodoukan_mapper import (
    shodoukan_entry_page_to_dictionary,
    shodoukan_entry_to_dictionary,
    shodoukan_entry_to_practice,
    shodoukan_kanji_to_dictionary,
    shodoukan_kanji_to_practice,
    shodoukan_search_to_dictionary,
)

__all__ = [
    "ShodoukanDictionaryGateway",
    "ShodoukanKanaGateway",
    "shodoukan_entry_page_to_dictionary",
    "shodoukan_entry_to_dictionary",
    "shodoukan_entry_to_practice",
    "shodoukan_kanji_to_dictionary",
    "shodoukan_kanji_to_practice",
    "shodoukan_search_to_dictionary",
]
