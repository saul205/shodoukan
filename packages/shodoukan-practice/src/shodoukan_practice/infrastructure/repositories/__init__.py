"""SQLAlchemy implementations of the domain repository ports.

They take a `Session`, flush to surface ids and constraint errors, and never
commit: the use case or request that opened the session owns the transaction.
Every query is scoped to the owning user.
"""

from .sqlalchemy_entry_collection_repository import SqlAlchemyEntryCollectionRepository
from .sqlalchemy_exercise_repository import SqlAlchemyExerciseRepository
from .sqlalchemy_exercise_session_repository import (
    SqlAlchemyExerciseSessionRepository,
)
from .sqlalchemy_exercise_statistics_repository import (
    SqlAlchemyExerciseStatisticsRepository,
)
from .sqlalchemy_kanji_collection_repository import SqlAlchemyKanjiCollectionRepository
from .sqlalchemy_practice_entry_repository import SqlAlchemyPracticeEntryRepository
from .sqlalchemy_practice_kanji_repository import SqlAlchemyPracticeKanjiRepository
from .sqlalchemy_user_repository import SqlAlchemyUserRepository

__all__ = [
    "SqlAlchemyEntryCollectionRepository",
    "SqlAlchemyExerciseRepository",
    "SqlAlchemyExerciseSessionRepository",
    "SqlAlchemyExerciseStatisticsRepository",
    "SqlAlchemyKanjiCollectionRepository",
    "SqlAlchemyPracticeEntryRepository",
    "SqlAlchemyPracticeKanjiRepository",
    "SqlAlchemyUserRepository",
]
