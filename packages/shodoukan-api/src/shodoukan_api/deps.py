from functools import lru_cache

from shodoukan import Dictionary


@lru_cache(maxsize=1)
def _get_dictionary() -> Dictionary:
    return Dictionary()


def dictionary_dep() -> Dictionary:
    return _get_dictionary()
