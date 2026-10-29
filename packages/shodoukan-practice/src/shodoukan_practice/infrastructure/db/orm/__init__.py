"""SQLAlchemy ORM models, one module per aggregate.

Importing this package registers every table on `Base.metadata`, which is
what Alembic and `create_all` use.
"""

from .base_orm import Base
from .entry_collection_orm import (
    EntryCollectionORM,
    EntryCollectionPublicationORM,
    entry_collection_dismissed_items,
    entry_collection_downloads,
    entry_collection_items,
)
from .exercise_orm import (
    ExerciseEntryCollectionORM,
    ExerciseKanjiCollectionORM,
    ExerciseORM,
)
from .exercise_session_orm import ExerciseQuestionORM, ExerciseSessionORM
from .kanji_collection_orm import (
    KanjiCollectionORM,
    KanjiCollectionPublicationORM,
    kanji_collection_dismissed_items,
    kanji_collection_downloads,
    kanji_collection_items,
)
from .practice_entry_orm import (
    PracticeEntryKanjiReadingORM,
    PracticeEntryORM,
    PracticeEntryReadingORM,
    PracticeGlossORM,
    PracticeSenseORM,
)
from .practice_kanji_orm import (
    PracticeKanjiMeaningORM,
    PracticeKanjiORM,
    PracticeKanjiReadingItemORM,
)
from .practice_sentence_orm import (
    PracticeSentenceORM,
    PracticeSentenceTranslationORM,
    PracticeSentenceWordORM,
)
from .user_orm import UserORM

__all__ = [
    "Base",
    "EntryCollectionORM",
    "EntryCollectionPublicationORM",
    "ExerciseEntryCollectionORM",
    "ExerciseKanjiCollectionORM",
    "ExerciseORM",
    "ExerciseQuestionORM",
    "ExerciseSessionORM",
    "KanjiCollectionORM",
    "KanjiCollectionPublicationORM",
    "PracticeEntryKanjiReadingORM",
    "PracticeEntryORM",
    "PracticeEntryReadingORM",
    "PracticeGlossORM",
    "PracticeKanjiMeaningORM",
    "PracticeKanjiORM",
    "PracticeKanjiReadingItemORM",
    "PracticeSenseORM",
    "PracticeSentenceORM",
    "PracticeSentenceTranslationORM",
    "PracticeSentenceWordORM",
    "UserORM",
    "entry_collection_dismissed_items",
    "entry_collection_downloads",
    "entry_collection_items",
    "kanji_collection_dismissed_items",
    "kanji_collection_downloads",
    "kanji_collection_items",
]
