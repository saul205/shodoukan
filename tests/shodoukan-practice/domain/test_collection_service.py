from datetime import UTC, datetime
from uuid import UUID

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

NOW = datetime(2026, 1, 1, tzinfo=UTC)
USER_ID = UUID("8f14e45f-ceea-467a-9575-2ad4a6a1a001")
OTHER_USER_ID = UUID("8f14e45f-ceea-467a-9575-2ad4a6a1a002")


def make_collection(
    cls: type[Collection] = EntryCollection,
    user_id: UUID = USER_ID,
    name: str = "verbs",
) -> Collection:
    return cls(id=None, user_id=user_id, name=name, created_at=NOW, updated_at=NOW)


def test_same_user_and_kind_are_combinable() -> None:
    ensure_combinable([make_collection(name="verbs"), make_collection(name="n5")])


def test_no_collections_are_combinable() -> None:
    ensure_combinable([])


def test_collections_of_different_users_are_not_combinable() -> None:
    with pytest.raises(CollectionOwnershipError):
        ensure_combinable(
            [make_collection(user_id=USER_ID), make_collection(user_id=OTHER_USER_ID)]
        )


def test_entry_and_kanji_collections_are_not_combinable() -> None:
    with pytest.raises(CollectionKindMismatchError):
        ensure_combinable(
            [make_collection(EntryCollection), make_collection(KanjiCollection)]
        )
