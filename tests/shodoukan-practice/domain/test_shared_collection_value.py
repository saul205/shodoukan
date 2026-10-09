import pytest
from pydantic import ValidationError

from shodoukan_practice.domain.entities import (
    MAX_SHARED_ITEMS,
    SharedEntry,
    SharedEntryCollection,
    SharedExample,
    SharedMeaning,
    SharedReading,
    SharedSense,
    SharedSentence,
    SharedSpelling,
)


def own_sense() -> SharedSense:
    return SharedSense(
        origin="added", glosses=[SharedMeaning(origin="added", text="x", lang="eng")]
    )


def test_provenance_is_the_ids_it_has() -> None:
    assert SharedReading(
        origin="added", id=3, copied_from_id=9, text="あ"
    ).provenance == {
        3,
        9,
    }
    assert SharedReading(origin="added", text="あ").provenance == set()


def test_a_word_of_ones_own_needs_a_reading_and_no_dictionary_parts() -> None:
    reading = SharedReading(origin="added", text="さんびき")
    SharedEntry(source_entry_id=None, readings=[reading], senses=[own_sense()])
    with pytest.raises(ValidationError, match="needs a reading"):
        SharedEntry(source_entry_id=None, senses=[own_sense()])
    with pytest.raises(ValidationError, match="no dictionary parts"):
        SharedEntry(
            source_entry_id=None,
            readings=[reading, SharedReading(origin="imported", text="さん")],
        )


def test_added_parts_are_checked_like_the_users_own() -> None:
    with pytest.raises(ValidationError, match="kana"):
        SharedReading(origin="added", text="sanbiki")
    with pytest.raises(ValidationError, match="spelling"):
        SharedSpelling(origin="added", text="  ")
    with pytest.raises(ValidationError, match="meaning"):
        SharedMeaning(origin="added", text="", lang="eng")
    with pytest.raises(ValidationError, match="Japanese sentence"):
        SharedExample(
            origin="added", sentences=[SharedSentence(lang="eng", text="Hi.")]
        )
    # The dictionary's are only located, never checked.
    SharedReading(origin="imported", text="anything")


def test_a_sense_of_ones_own_has_meanings_in_one_language() -> None:
    with pytest.raises(ValidationError, match="needs a meaning"):
        SharedSense(origin="added")
    with pytest.raises(ValidationError, match="one language"):
        SharedSense(
            origin="added",
            glosses=[
                SharedMeaning(origin="added", text="eat", lang="eng"),
                SharedMeaning(origin="added", text="comer", lang="spa"),
            ],
        )
    with pytest.raises(ValidationError, match="no dictionary parts"):
        SharedSense(
            origin="added",
            glosses=[SharedMeaning(origin="imported", text="eat", lang="eng")],
        )


def test_a_collection_is_bounded() -> None:
    item = SharedEntry(source_entry_id=1)
    with pytest.raises(ValidationError):
        SharedEntryCollection(name="N5", items=[item] * (MAX_SHARED_ITEMS + 1))
    with pytest.raises(ValidationError):
        SharedEntryCollection(name="")
