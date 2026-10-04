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
    "GetDictionaryEntry",
    "GetDictionaryKanji",
    "GetEntryCollection",
    "GetExercise",
    "GetImportStatus",
    "GetKanjiCollection",
    "GetLibraryEntry",
    "GetLibraryKanji",
    "ImportStatus",
    "LibraryPage",
    "ListCollectionsOfEntry",
    "ListCollectionsOfKanji",
    "ListEntriesForKanji",
    "ListEntryCollections",
    "ListExercises",
    "ListKanjiCollections",
    "ListKanjiForEntry",
    "SearchDictionary",
    "SearchEntries",
    "SearchKanji",
    "build_search",
    "resolve_scope",
]
