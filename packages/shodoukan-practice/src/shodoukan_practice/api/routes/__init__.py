"""HTTP routes, one module per subject."""

from .dictionary_routes import router as dictionary_router
from .library_routes import router as library_router
from .user_routes import router as user_router

__all__ = ["dictionary_router", "library_router", "user_router"]
