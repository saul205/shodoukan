from datetime import datetime

import pytest
from pydantic import ValidationError

from shodoukan_practice.domain.entities import (
    Collection,
    EntryCollection,
    KanjiCollection,
)

NOW = datetime(2026, 1, 1)


def make_collection(
    cls: type[Collection] = EntryCollection,
    user_id: int = 1,
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
