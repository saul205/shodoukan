"""SQLAlchemy implementations of the domain repository ports.

They take a `Session`, flush to surface ids and constraint errors, and never
commit: the use case or request that opened the session owns the transaction.
Every query is scoped to the owning user.
"""

from .sqlalchemy_entry_collection_repository import SqlAlchemyEntryCollectionRepository
from .sqlalchemy_kanji_collection_repository import SqlAlchemyKanjiCollectionRepository
from .sqlalchemy_practice_entry_repository import SqlAlchemyPracticeEntryRepository
from .sqlalchemy_practice_kanji_repository import SqlAlchemyPracticeKanjiRepository
from .sqlalchemy_user_repository import SqlAlchemyUserRepository

__all__ = [
    "SqlAlchemyEntryCollectionRepository",
    "SqlAlchemyKanjiCollectionRepository",
    "SqlAlchemyPracticeEntryRepository",
    "SqlAlchemyPracticeKanjiRepository",
    "SqlAlchemyUserRepository",
]
