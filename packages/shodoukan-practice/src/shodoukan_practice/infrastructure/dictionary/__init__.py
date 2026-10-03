"""The shodoukan dictionary, used in-process through the `shodoukan` library."""

from .shodoukan_dictionary_gateway import ShodoukanDictionaryGateway
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
    "shodoukan_entry_page_to_dictionary",
    "shodoukan_entry_to_dictionary",
    "shodoukan_entry_to_practice",
    "shodoukan_kanji_to_dictionary",
    "shodoukan_kanji_to_practice",
    "shodoukan_search_to_dictionary",
]
