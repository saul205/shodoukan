"""SQLAlchemy ORM models, one module per aggregate.

Importing this package registers every table on `Base.metadata`, which is
what Alembic and `create_all` use.
"""

from .base_orm import Base
from .entry_collection_orm import EntryCollectionORM, entry_collection_items
from .exercise_orm import (
    ExerciseEntryCollectionORM,
    ExerciseKanjiCollectionORM,
    ExerciseORM,
)
from .exercise_session_orm import ExerciseQuestionORM, ExerciseSessionORM
from .kanji_collection_orm import KanjiCollectionORM, kanji_collection_items
from .practice_entry_orm import (
    PracticeEntryKanjiReadingORM,
    PracticeEntryORM,
    PracticeEntryReadingORM,
    PracticeExampleORM,
    PracticeExampleSentenceORM,
    PracticeGlossORM,
    PracticeSenseORM,
)
from .practice_kanji_orm import (
    PracticeKanjiMeaningORM,
    PracticeKanjiORM,
    PracticeKanjiReadingItemORM,
)
from .user_orm import UserORM

__all__ = [
    "Base",
    "EntryCollectionORM",
    "ExerciseEntryCollectionORM",
    "ExerciseKanjiCollectionORM",
    "ExerciseORM",
    "ExerciseQuestionORM",
    "ExerciseSessionORM",
    "KanjiCollectionORM",
    "PracticeEntryKanjiReadingORM",
    "PracticeEntryORM",
    "PracticeEntryReadingORM",
    "PracticeExampleORM",
    "PracticeExampleSentenceORM",
    "PracticeGlossORM",
    "PracticeKanjiMeaningORM",
    "PracticeKanjiORM",
    "PracticeKanjiReadingItemORM",
    "PracticeSenseORM",
    "UserORM",
    "entry_collection_items",
    "kanji_collection_items",
]
