"""Request/response models, one module per subject."""

from .collection_schemas import CollectionRequest, CollectionResponse
from .dictionary_schemas import (
    DictionaryEntryPageResponse,
    DictionaryEntryResponse,
    DictionaryKanjiResponse,
    DictionarySearchResponse,
)
from .library_schemas import (
    ImportedEntryResponse,
    ImportedKanjiResponse,
    ImportEntryRequest,
    ImportKanjiRequest,
    ImportStatusResponse,
    PracticeEntryPageResponse,
    PracticeEntryResponse,
    PracticeKanjiPageResponse,
    PracticeKanjiResponse,
)
from .user_schemas import UserResponse

__all__ = [
    "CollectionRequest",
    "CollectionResponse",
    "DictionaryEntryPageResponse",
    "DictionaryEntryResponse",
    "DictionaryKanjiResponse",
    "DictionarySearchResponse",
    "ImportEntryRequest",
    "ImportKanjiRequest",
    "ImportStatusResponse",
    "ImportedEntryResponse",
    "ImportedKanjiResponse",
    "PracticeEntryPageResponse",
    "PracticeEntryResponse",
    "PracticeKanjiPageResponse",
    "PracticeKanjiResponse",
    "UserResponse",
]
