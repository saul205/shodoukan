"""The user's free-text notes, shared by every entity that can carry them."""

from typing import Annotated

from pydantic import AfterValidator, Field, TypeAdapter

NOTES_MAX_LENGTH = 2000


def clean_notes(notes: str | None) -> str | None:
    """Strip surrounding whitespace; a blank note is no note."""
    if notes is None:
        return None
    return notes.strip() or None


Notes = Annotated[
    str | None, Field(max_length=NOTES_MAX_LENGTH), AfterValidator(clean_notes)
]

_NOTES: TypeAdapter[str | None] = TypeAdapter(Notes)


def parse_notes(notes: str | None) -> str | None:
    """Validate and clean a note like a `Notes` field does.

    For nested models, which don't validate on assignment. Raises
    `pydantic.ValidationError` if it's too long.
    """
    return _NOTES.validate_python(notes)
