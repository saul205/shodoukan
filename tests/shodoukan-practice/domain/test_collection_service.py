from datetime import datetime

import pytest

from shodoukan_practice.domain.entities import (
    Collection,
    EntryCollection,
    KanjiCollection,
)
from shodoukan_practice.domain.exceptions import (
    CollectionKindMismatchError,
    CollectionOwnershipError,
)
from shodoukan_practice.domain.services import ensure_combinable

NOW = datetime(2026, 1, 1)


def make_collection(
    cls: type[Collection] = EntryCollection,
    user_id: int = 1,
    name: str = "verbs",
) -> Collection:
    return cls(id=None, user_id=user_id, name=name, created_at=NOW, updated_at=NOW)


def test_same_user_and_kind_are_combinable() -> None:
    ensure_combinable([make_collection(name="verbs"), make_collection(name="n5")])


def test_no_collections_are_combinable() -> None:
    ensure_combinable([])


def test_collections_of_different_users_are_not_combinable() -> None:
    with pytest.raises(CollectionOwnershipError):
        ensure_combinable([make_collection(user_id=1), make_collection(user_id=2)])


def test_entry_and_kanji_collections_are_not_combinable() -> None:
    with pytest.raises(CollectionKindMismatchError):
        ensure_combinable(
            [make_collection(EntryCollection), make_collection(KanjiCollection)]
        )
