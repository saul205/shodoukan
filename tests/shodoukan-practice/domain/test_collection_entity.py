from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from shodoukan_practice.domain.entities import (
    COLLECTION_NAME_MAX_LENGTH,
    Collection,
    EntryCollection,
    KanjiCollection,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
USER_ID = UUID("8f14e45f-ceea-467a-9575-2ad4a6a1a001")
OTHER_USER_ID = UUID("8f14e45f-ceea-467a-9575-2ad4a6a1a002")


def make_collection(
    cls: type[Collection] = EntryCollection,
    user_id: UUID = USER_ID,
    name: str = "verbs",
) -> Collection:
    return cls(id=None, user_id=user_id, name=name, created_at=NOW, updated_at=NOW)


def test_collection_defaults() -> None:
    assert make_collection().description is None


def test_collection_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        make_collection(name="")


def test_subclasses_are_collections() -> None:
    assert isinstance(make_collection(EntryCollection), Collection)
    assert isinstance(make_collection(KanjiCollection), Collection)


def test_collection_serializes_round_trip() -> None:
    collection = make_collection(KanjiCollection)
    assert KanjiCollection.model_validate(collection.model_dump()) == collection


def test_rename_touches() -> None:
    collection = make_collection()
    collection.rename("nouns")

    assert collection.name == "nouns"
    assert collection.updated_at > NOW


def test_rename_to_same_name_does_not_touch() -> None:
    collection = make_collection(name="verbs")
    collection.rename("verbs")

    assert collection.updated_at == NOW


def test_rename_validates_the_name() -> None:
    with pytest.raises(ValidationError):
        make_collection().rename("")


def test_describe_touches() -> None:
    collection = make_collection()
    collection.describe("Godan and ichidan")

    assert collection.description == "Godan and ichidan"
    assert collection.updated_at > NOW


def test_collection_name_is_at_most_100_characters() -> None:
    assert make_collection(name="x" * COLLECTION_NAME_MAX_LENGTH).name
    with pytest.raises(ValidationError):
        make_collection(name="x" * (COLLECTION_NAME_MAX_LENGTH + 1))
