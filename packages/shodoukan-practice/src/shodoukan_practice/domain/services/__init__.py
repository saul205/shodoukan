"""Pure business logic, one module per subject: validation rules and, later,
effective field values from overrides."""

from .collection_service import ensure_combinable

__all__ = ["ensure_combinable"]
