"""HTTP routes, one module per subject."""

from .library_routes import router as library_router

__all__ = ["library_router"]
