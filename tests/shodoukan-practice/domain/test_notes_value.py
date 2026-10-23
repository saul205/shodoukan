import pytest
from pydantic import TypeAdapter, ValidationError

from shodoukan_practice.domain.entities import NOTES_MAX_LENGTH, Notes

notes: TypeAdapter[str | None] = TypeAdapter(Notes)


def test_notes_are_stripped_and_blank_is_none() -> None:
    assert notes.validate_python("  remember the okurigana \n") == (
        "remember the okurigana"
    )
    assert notes.validate_python("   ") is None
    assert notes.validate_python(None) is None


def test_notes_have_a_maximum_length() -> None:
    assert notes.validate_python("x" * NOTES_MAX_LENGTH)
    with pytest.raises(ValidationError):
        notes.validate_python("x" * (NOTES_MAX_LENGTH + 1))
