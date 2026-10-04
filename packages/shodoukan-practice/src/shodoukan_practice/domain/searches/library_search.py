"""What a search of the library asks for, and where it looks.

These are plain values: the item repositories run the search (`find`,
`count`) and the search use cases build it from what the user typed.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Generic, TypeVar

from ..entities import Collection
from ..gateways import KanaForms

C = TypeVar("C", bound=Collection)


class MatchTier(IntEnum):
    """How well an item matches; a better tier always ranks first."""

    CONTAINS = 1
    """The query is somewhere in a spelling, reading or meaning."""
    PREFIX = 2
    """A spelling or reading starts with it, or a word of a meaning does."""
    EXACT = 3
    """A spelling, reading or meaning is the query."""


@dataclass(frozen=True)
class LibrarySearch:
    """Filters for a search; with no `text`, every item in scope matches.

    - `text`: what the user typed, trimmed and lower-cased.
    - `kana`: `text` in hiragana and katakana, if it reads as romaji or kana.
    - `meaning_lang`: the language of the meanings to look in, as the items
      store it (`eng` for entry glosses, `en` for kanji); `None` for any.
    - `active`: only active (`True`) or inactive (`False`) items; `None` for all.

    Readings and meanings match whether they're enabled or not.
    """

    text: str | None = None
    kana: KanaForms | None = None
    meaning_lang: str | None = None
    active: bool | None = None

    @property
    def needles(self) -> tuple[str, ...]:
        """The forms to look for in spellings and readings, without repeats."""
        if self.text is None:
            return ()
        forms = [self.text, *(self.kana or ())]
        return tuple(dict.fromkeys(forms))


@dataclass(frozen=True)
class WholeLibrary:
    """Every item of the user's library."""


@dataclass(frozen=True)
class InCollection(Generic[C]):
    """Only the collection's items, in the order they were added."""

    collection: C


@dataclass(frozen=True)
class NotInCollection(Generic[C]):
    """The library minus the collection's items (what can still be added)."""

    collection: C


SearchScope = WholeLibrary | InCollection[C] | NotInCollection[C]
