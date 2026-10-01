"""Dependency wiring: concrete infrastructure behind the domain ports."""

from functools import lru_cache

from shodoukan import Dictionary

from ..domain.gateways import DictionaryGateway
from ..infrastructure.dictionary import ShodoukanDictionaryGateway


@lru_cache(maxsize=1)
def _get_dictionary() -> Dictionary:
    # Read-only and thread-safe to share: one instance per process. The
    # database path comes from SHODOUKAN_DB_PATH (or the library's default);
    # it's downloaded on first use if missing, as in shodoukan-api.
    return Dictionary()


def get_dictionary_gateway() -> DictionaryGateway:
    return ShodoukanDictionaryGateway(_get_dictionary())
