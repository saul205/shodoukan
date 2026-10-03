"""Read use cases, one module per subject."""

from .collection_queries import (
    GetEntryCollection,
    GetKanjiCollection,
    ListEntryCollectionItems,
    ListEntryCollections,
    ListKanjiCollectionItems,
    ListKanjiCollections,
)
from .dictionary_queries import (
    GetDictionaryEntry,
    GetDictionaryKanji,
    ListEntriesForKanji,
    ListKanjiForEntry,
    SearchDictionary,
)
from .library_queries import (
    GetImportStatus,
    GetLibraryEntry,
    GetLibraryKanji,
    ImportStatus,
    LibraryPage,
    ListCollectionsOfEntry,
    ListCollectionsOfKanji,
    ListLibraryEntries,
    ListLibraryKanji,
)

__all__ = [
    "GetDictionaryEntry",
    "GetDictionaryKanji",
    "GetEntryCollection",
    "GetImportStatus",
    "GetKanjiCollection",
    "GetLibraryEntry",
    "GetLibraryKanji",
    "ImportStatus",
    "LibraryPage",
    "ListCollectionsOfEntry",
    "ListCollectionsOfKanji",
    "ListEntriesForKanji",
    "ListEntryCollectionItems",
    "ListEntryCollections",
    "ListKanjiCollectionItems",
    "ListKanjiCollections",
    "ListKanjiForEntry",
    "ListLibraryEntries",
    "ListLibraryKanji",
    "SearchDictionary",
]
