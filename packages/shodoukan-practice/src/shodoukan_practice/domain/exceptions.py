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


class LastReadingError(ValueError):
    """The only reading of an entry was removed: a word always keeps one."""


class LastMeaningError(ValueError):
    """The only meaning of a sense was removed: a sense always keeps one.

    To get rid of an own sense, remove the sense itself.
    """


class SenseLanguageError(ValueError):
    """A meaning in another language was added to a sense: like JMDict's, a
    sense's meanings are all in one language."""


class ExercisePoolTooSmallError(ValueError):
    """An exercise's collections don't have enough usable items to ask about."""


class QuestionNotActiveError(ValueError):
    """An answer to a question that isn't the session's active one (answered
    already, or replaced), or a question asked while another is active."""


class SessionFinishedError(ValueError):
    """The exercise session is closed: no more questions or answers."""


class InvalidAnswerError(ValueError):
    """An answer that doesn't fit its question (e.g. an option it doesn't have)."""


class SessionAlreadyOpenError(ValueError):
    """The user already has an open exercise session (one was started
    meanwhile); a user studies one session at a time."""
