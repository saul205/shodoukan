"""Domain-level exceptions."""


class CollectionOwnershipError(ValueError):
    """Collections owned by different users were combined."""


class CollectionKindMismatchError(ValueError):
    """Entry collections and kanji collections were combined."""


class EntityNotFoundError(LookupError):
    """The entity doesn't exist or doesn't belong to the given user."""
