import pytest
from factories import make_entry, make_entry_collection
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import PracticeEntry
from shodoukan_practice.domain.exceptions import (
    CollectionNameTakenError,
    CollectionOwnershipError,
    EntityNotFoundError,
)
from shodoukan_practice.domain.searches import InCollection, LibrarySearch
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
)

# Searches without text: they list the scope, like the library pages.
ACTIVE = LibrarySearch(active=True)


@pytest.fixture
def repo(session: Session) -> SqlAlchemyEntryCollectionRepository:
    return SqlAlchemyEntryCollectionRepository(session)


@pytest.fixture
def items(session: Session, user: UserORM) -> list[PracticeEntry]:
    item_repo = SqlAlchemyPracticeEntryRepository(session)
    return [
        item_repo.add(make_entry(user.id, 1)),
        item_repo.add(make_entry(user.id, 2)),
        item_repo.add(make_entry(user.id, 3, is_active=False)),
    ]


def test_add_get_and_list_for_user(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, other_user: UserORM
) -> None:
    b = repo.add(make_entry_collection(user.id, "b"))
    a = repo.add(make_entry_collection(user.id, "a"))
    repo.add(make_entry_collection(other_user.id, "theirs"))

    assert b.id is not None
    assert repo.get(b.id, user.id) == b
    assert repo.get(b.id, other_user.id) is None
    assert repo.list_for_user(user.id) == [a, b]


def test_update_renames(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    renamed = repo.update(collection.model_copy(update={"name": "renamed"}))

    assert collection.id is not None
    assert repo.get(collection.id, user.id) == renamed
    assert renamed.name == "renamed"


def test_update_of_another_users_collection_fails(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, other_user: UserORM
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    with pytest.raises(EntityNotFoundError):
        repo.update(collection.model_copy(update={"user_id": other_user.id}))


def test_add_item_is_idempotent(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, items: list[PracticeEntry]
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    repo.add_item(collection, items[0])
    repo.add_item(collection, items[0])

    assert repo.item_ids([collection]) == {items[0].id}


def test_add_item_of_another_user_fails(
    repo: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    other_user: UserORM,
    items: list[PracticeEntry],
) -> None:
    theirs = repo.add(make_entry_collection(other_user.id))
    with pytest.raises(CollectionOwnershipError):
        repo.add_item(theirs, items[0])


def test_remove_item(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, items: list[PracticeEntry]
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    repo.add_item(collection, items[0])
    repo.remove_item(collection, items[0])
    repo.remove_item(collection, items[0])

    assert repo.item_ids([collection]) == set()


def test_find_in_a_collection_paginates_and_filters_by_active(
    session: Session,
    repo: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    items: list[PracticeEntry],
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    for item in items:
        repo.add_item(collection, item)
    item_repo = SqlAlchemyPracticeEntryRepository(session)

    in_collection = InCollection(collection)
    first = item_repo.find(user.id, ACTIVE, in_collection, limit=1, offset=0)
    rest = item_repo.find(user.id, ACTIVE, in_collection, limit=10, offset=1)
    every = item_repo.find(user.id, LibrarySearch(), in_collection, limit=10, offset=0)

    assert first == [items[0]]
    assert rest == [items[1]]
    assert every == items


def test_list_for_item_returns_its_collections(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, items: list[PracticeEntry]
) -> None:
    b = repo.add(make_entry_collection(user.id, "b"))
    a = repo.add(make_entry_collection(user.id, "a"))
    repo.add(make_entry_collection(user.id, "unrelated"))
    repo.add_item(b, items[0])
    repo.add_item(a, items[0])

    assert repo.list_for_item(items[0]) == [a, b]


def test_item_ids_are_distinct_and_active_only(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, items: list[PracticeEntry]
) -> None:
    one = repo.add(make_entry_collection(user.id, "one"))
    two = repo.add(make_entry_collection(user.id, "two"))
    repo.add_item(one, items[0])
    repo.add_item(two, items[0])
    repo.add_item(two, items[1])
    repo.add_item(two, items[2])  # inactive

    assert repo.item_ids([one, two]) == {items[0].id, items[1].id}


def test_delete_keeps_the_items(
    session: Session,
    repo: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    items: list[PracticeEntry],
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    repo.add_item(collection, items[0])
    repo.delete(collection)

    assert collection.id is not None
    assert items[0].id is not None
    assert repo.get(collection.id, user.id) is None
    assert repo.list_for_item(items[0]) == []
    assert (
        SqlAlchemyPracticeEntryRepository(session).get(items[0].id, user.id) is not None
    )


def test_add_with_a_taken_name_fails_and_keeps_the_session_usable(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, other_user: UserORM
) -> None:
    kept = repo.add(make_entry_collection(user.id, "same"))
    theirs = repo.add(make_entry_collection(other_user.id, "same"))

    with pytest.raises(CollectionNameTakenError):
        repo.add(make_entry_collection(user.id, "same"))

    assert theirs.name == "same"  # names are unique per user only
    assert repo.list_for_user(user.id) == [kept]


def test_update_to_a_taken_name_fails(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM
) -> None:
    repo.add(make_entry_collection(user.id, "a"))
    b = repo.add(make_entry_collection(user.id, "b"))

    with pytest.raises(CollectionNameTakenError):
        repo.update(b.model_copy(update={"name": "a"}))

    assert b.id is not None
    assert repo.get(b.id, user.id) == b
