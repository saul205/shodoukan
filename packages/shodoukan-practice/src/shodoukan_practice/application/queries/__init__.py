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
    ImportStatus,
    LibraryPage,
    ListLibraryEntries,
    ListLibraryKanji,
)

__all__ = [
    "GetDictionaryEntry",
    "GetDictionaryKanji",
    "GetEntryCollection",
    "GetImportStatus",
    "GetKanjiCollection",
    "ImportStatus",
    "LibraryPage",
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
