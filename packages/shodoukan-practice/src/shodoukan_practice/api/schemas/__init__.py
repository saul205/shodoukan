"""Request/response models, one module per subject."""

from .collection_schemas import CollectionRequest, CollectionResponse
from .dictionary_schemas import (
    DictionaryEntryPageResponse,
    DictionaryEntryResponse,
    DictionaryKanjiResponse,
    DictionarySearchResponse,
)
from .exercise_schemas import ExerciseRequest, ExerciseResponse, NewExerciseRequest
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
from .library_search_schemas import MeaningLang, NotInCollection, SearchText
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
    "ExerciseRequest",
    "ExerciseResponse",
    "ImportEntryRequest",
    "ImportKanjiRequest",
    "ImportStatusResponse",
    "ImportedEntryResponse",
    "ImportedKanjiResponse",
    "MeaningLang",
    "MeaningTextRequest",
    "NewExerciseRequest",
    "NewGlossRequest",
    "NewKanjiMeaningRequest",
    "NotInCollection",
    "NotesRequest",
    "PracticeEntryPageResponse",
    "PracticeEntryResponse",
    "PracticeKanjiPageResponse",
    "PracticeKanjiResponse",
    "SearchText",
    "UserResponse",
]
