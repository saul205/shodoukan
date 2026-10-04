"""Domain-level exceptions."""


class CollectionOwnershipError(ValueError):
    """Collections owned by different users were combined."""


class CollectionKindMismatchError(ValueError):
    """Entry collections and kanji collections were combined."""


class EntityNotFoundError(LookupError):
    """The entity doesn't exist or doesn't belong to the given user."""


class DictionaryItemNotFoundError(LookupError):
    """The dictionary has no entry or kanji with the requested id."""


class CollectionNameTakenError(ValueError):
    """The user already has a collection of that kind with that name."""


class OriginalDataError(ValueError):
    """Dictionary data in the library was edited or removed.

    Imported items can only be disabled; only the user's own can change.
    """


class ExercisePoolTooSmallError(ValueError):
    """An exercise's collections don't have enough usable items to ask about."""


class QuestionAnsweredError(ValueError):
    """A question of an exercise session was answered already."""


class InvalidAnswerError(ValueError):
    """An answer that doesn't fit its question (e.g. an option it doesn't have)."""
