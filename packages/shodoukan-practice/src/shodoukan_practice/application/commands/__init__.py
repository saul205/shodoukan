"""Write use cases, one module per subject."""

from .collection_commands import (
    AddEntryToCollection,
    AddKanjiToCollection,
    CreateEntryCollection,
    CreateKanjiCollection,
    DeleteEntryCollection,
    DeleteKanjiCollection,
    RemoveEntryFromCollection,
    RemoveKanjiFromCollection,
    UpdateEntryCollection,
    UpdateKanjiCollection,
)
from .library_commands import ImportEntry, ImportKanji, ImportResult
from .practice_entry_commands import (
    AddEntryGloss,
    EditEntryGloss,
    RemoveEntryFromLibrary,
    RemoveEntryGloss,
    SetEntryActive,
    SetEntryNotes,
    SetEntryPartEnabled,
    SetSenseNotes,
)
from .practice_kanji_commands import (
    AddKanjiMeaning,
    EditKanjiMeaning,
    RemoveKanjiFromLibrary,
    RemoveKanjiMeaning,
    SetKanjiActive,
    SetKanjiNotes,
    SetKanjiPartEnabled,
)
from .user_commands import EnsureUser

__all__ = [
    "AddEntryGloss",
    "AddEntryToCollection",
    "AddKanjiMeaning",
    "AddKanjiToCollection",
    "CreateEntryCollection",
    "CreateKanjiCollection",
    "DeleteEntryCollection",
    "DeleteKanjiCollection",
    "EditEntryGloss",
    "EditKanjiMeaning",
    "EnsureUser",
    "ImportEntry",
    "ImportKanji",
    "ImportResult",
    "RemoveEntryFromCollection",
    "RemoveEntryFromLibrary",
    "RemoveEntryGloss",
    "RemoveKanjiFromCollection",
    "RemoveKanjiFromLibrary",
    "RemoveKanjiMeaning",
    "SetEntryActive",
    "SetEntryNotes",
    "SetEntryPartEnabled",
    "SetKanjiActive",
    "SetKanjiNotes",
    "SetKanjiPartEnabled",
    "SetSenseNotes",
    "UpdateEntryCollection",
    "UpdateKanjiCollection",
]
