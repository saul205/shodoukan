"""Read use cases, one module per subject."""

from .collection_queries import (
    GetEntryCollection,
    GetKanjiCollection,
    ListEntryCollections,
    ListKanjiCollections,
)
from .dictionary_queries import (
    GetDictionaryEntry,
    GetDictionaryKanji,
    ListEntriesForKanji,
    ListKanjiForEntry,
    SearchDictionary,
)
from .exercise_queries import GetExercise, ListExercises
from .exercise_session_queries import (
    GetExerciseSession,
    ListExerciseSessions,
    SessionSummaryPage,
)
from .exercise_statistics_queries import (
    MAX_ACTIVITY_DAYS,
    MOST_MISSED_LIMIT,
    DayActivity,
    ExerciseStatistics,
    GetExerciseStatistics,
    GetPracticeStatistics,
    MissedItem,
    PracticeStatistics,
)
from .library_queries import (
    GetImportStatus,
    GetLibraryEntry,
    GetLibraryKanji,
    ImportStatus,
    LibraryPage,
    ListCollectionsOfEntry,
    ListCollectionsOfKanji,
)
from .library_search_queries import (
    SearchEntries,
    SearchKanji,
    build_search,
    resolve_scope,
)

__all__ = [
    "MAX_ACTIVITY_DAYS",
    "MOST_MISSED_LIMIT",
    "DayActivity",
    "ExerciseStatistics",
    "GetDictionaryEntry",
    "GetDictionaryKanji",
    "GetEntryCollection",
    "GetExercise",
    "GetExerciseSession",
    "GetExerciseStatistics",
    "GetImportStatus",
    "GetKanjiCollection",
    "GetLibraryEntry",
    "GetLibraryKanji",
    "GetPracticeStatistics",
    "ImportStatus",
    "LibraryPage",
    "ListCollectionsOfEntry",
    "ListCollectionsOfKanji",
    "ListEntriesForKanji",
    "ListEntryCollections",
    "ListExerciseSessions",
    "ListExercises",
    "ListKanjiCollections",
    "ListKanjiForEntry",
    "MissedItem",
    "PracticeStatistics",
    "SearchDictionary",
    "SearchEntries",
    "SearchKanji",
    "SessionSummaryPage",
    "build_search",
    "resolve_scope",
]
