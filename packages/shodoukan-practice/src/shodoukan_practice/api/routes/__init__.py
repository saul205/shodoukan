"""HTTP routes, one module per subject."""

from .collection_routes import entry_router as entry_collection_router
from .collection_routes import kanji_router as kanji_collection_router
from .dictionary_routes import router as dictionary_router
from .exercise_routes import router as exercise_router
from .exercise_session_routes import router as exercise_session_router
from .library_routes import router as library_router
from .practice_entry_routes import router as practice_entry_router
from .practice_kanji_routes import router as practice_kanji_router
from .user_routes import router as user_router

__all__ = [
    "dictionary_router",
    "entry_collection_router",
    "exercise_router",
    "exercise_session_router",
    "kanji_collection_router",
    "library_router",
    "practice_entry_router",
    "practice_kanji_router",
    "user_router",
]
