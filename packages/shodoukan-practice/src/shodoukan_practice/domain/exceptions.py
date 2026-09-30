"""Domain-level exceptions."""


class CollectionOwnershipError(ValueError):
    """Collections owned by different users were combined."""


class CollectionKindMismatchError(ValueError):
    """Entry collections and kanji collections were combined."""
