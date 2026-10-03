"""Request/response models, one module per subject."""

from .collection_schemas import CollectionRequest, CollectionResponse
from .dictionary_schemas import (
    DictionaryEntryPageResponse,
    DictionaryEntryResponse,
    DictionaryKanjiResponse,
    DictionarySearchResponse,
)
from .library_schemas import (
    ActiveRequest,
    EnabledRequest,
    ImportedEntryResponse,
    ImportedKanjiResponse,
    ImportEntryRequest,
    ImportKanjiRequest,
    ImportStatusResponse,
    MeaningTextRequest,
    NewGlossRequest,
    NewKanjiMeaningRequest,
    NotesRequest,
    PracticeEntryPageResponse,
    PracticeEntryResponse,
    PracticeKanjiPageResponse,
    PracticeKanjiResponse,
)
from .user_schemas import UserResponse

__all__ = [
    "ActiveRequest",
    "CollectionRequest",
    "CollectionResponse",
    "DictionaryEntryPageResponse",
    "DictionaryEntryResponse",
    "DictionaryKanjiResponse",
    "DictionarySearchResponse",
    "EnabledRequest",
    "ImportEntryRequest",
    "ImportKanjiRequest",
    "ImportStatusResponse",
    "ImportedEntryResponse",
    "ImportedKanjiResponse",
    "MeaningTextRequest",
    "NewGlossRequest",
    "NewKanjiMeaningRequest",
    "NotesRequest",
    "PracticeEntryPageResponse",
    "PracticeEntryResponse",
    "PracticeKanjiPageResponse",
    "PracticeKanjiResponse",
    "UserResponse",
]
