"""Repository interfaces (ports).

Collection membership is stored in link tables and handled here, not on the
`Collection` entity. Methods that act on a collection take the typed entity
(`EntryCollection` / `KanjiCollection`) so entry and kanji collection ids,
which come from different tables, can't be mixed up.
"""

from .entry_collection_repository import EntryCollectionRepository
from .kanji_collection_repository import KanjiCollectionRepository
from .practice_entry_repository import PracticeEntryRepository
from .practice_kanji_repository import PracticeKanjiRepository
from .user_repository import UserRepository

__all__ = [
    "EntryCollectionRepository",
    "KanjiCollectionRepository",
    "PracticeEntryRepository",
    "PracticeKanjiRepository",
    "UserRepository",
]
