import pytest
from factories import make_kanji, make_kanji_collection
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import PracticeKanji
from shodoukan_practice.domain.exceptions import (
    CollectionNameTakenError,
    CollectionOwnershipError,
    EntityNotFoundError,
)
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeKanjiRepository,
)


@pytest.fixture
def repo(session: Session) -> SqlAlchemyKanjiCollectionRepository:
    return SqlAlchemyKanjiCollectionRepository(session)


@pytest.fixture
def items(session: Session, user: UserORM) -> list[PracticeKanji]:
    item_repo = SqlAlchemyPracticeKanjiRepository(session)
    return [
        item_repo.add(make_kanji(user.id, "食")),
        item_repo.add(make_kanji(user.id, "水")),
        item_repo.add(make_kanji(user.id, "火", is_active=False)),
    ]


def test_add_get_and_list_for_user(
    repo: SqlAlchemyKanjiCollectionRepository, user: UserORM, other_user: UserORM
) -> None:
    b = repo.add(make_kanji_collection(user.id, "b"))
    a = repo.add(make_kanji_collection(user.id, "a"))
    repo.add(make_kanji_collection(other_user.id, "theirs"))

    assert b.id is not None
    assert repo.get(b.id, user.id) == b
    assert repo.get(b.id, other_user.id) is None
    assert repo.list_for_user(user.id) == [a, b]


def test_update_renames(
    repo: SqlAlchemyKanjiCollectionRepository, user: UserORM
) -> None:
    collection = repo.add(make_kanji_collection(user.id))
    renamed = repo.update(collection.model_copy(update={"name": "renamed"}))

    assert collection.id is not None
    assert repo.get(collection.id, user.id) == renamed
    assert renamed.name == "renamed"


def test_update_of_another_users_collection_fails(
    repo: SqlAlchemyKanjiCollectionRepository, user: UserORM, other_user: UserORM
) -> None:
    collection = repo.add(make_kanji_collection(user.id))
    with pytest.raises(EntityNotFoundError):
        repo.update(collection.model_copy(update={"user_id": other_user.id}))


def test_add_item_is_idempotent(
    repo: SqlAlchemyKanjiCollectionRepository, user: UserORM, items: list[PracticeKanji]
) -> None:
    collection = repo.add(make_kanji_collection(user.id))
    repo.add_item(collection, items[0])
    repo.add_item(collection, items[0])

    assert repo.item_ids([collection]) == {items[0].id}


def test_add_item_of_another_user_fails(
    repo: SqlAlchemyKanjiCollectionRepository,
    user: UserORM,
    other_user: UserORM,
    items: list[PracticeKanji],
) -> None:
    theirs = repo.add(make_kanji_collection(other_user.id))
    with pytest.raises(CollectionOwnershipError):
        repo.add_item(theirs, items[0])


def test_remove_item(
    repo: SqlAlchemyKanjiCollectionRepository, user: UserORM, items: list[PracticeKanji]
) -> None:
    collection = repo.add(make_kanji_collection(user.id))
    repo.add_item(collection, items[0])
    repo.remove_item(collection, items[0])
    repo.remove_item(collection, items[0])

    assert repo.item_ids([collection]) == set()


def test_list_by_collection_paginates_and_skips_inactive(
    session: Session,
    repo: SqlAlchemyKanjiCollectionRepository,
    user: UserORM,
    items: list[PracticeKanji],
) -> None:
    collection = repo.add(make_kanji_collection(user.id))
    for item in items:
        repo.add_item(collection, item)
    item_repo = SqlAlchemyPracticeKanjiRepository(session)

    first = item_repo.list_by_collection(collection, limit=1, offset=0)
    rest = item_repo.list_by_collection(collection, limit=10, offset=1)

    assert first == [items[0]]
    assert rest == [items[1]]


def test_list_for_item_returns_its_collections(
    repo: SqlAlchemyKanjiCollectionRepository, user: UserORM, items: list[PracticeKanji]
) -> None:
    b = repo.add(make_kanji_collection(user.id, "b"))
    a = repo.add(make_kanji_collection(user.id, "a"))
    repo.add(make_kanji_collection(user.id, "unrelated"))
    repo.add_item(b, items[0])
    repo.add_item(a, items[0])

    assert repo.list_for_item(items[0]) == [a, b]


def test_item_ids_are_distinct_and_active_only(
    repo: SqlAlchemyKanjiCollectionRepository, user: UserORM, items: list[PracticeKanji]
) -> None:
    one = repo.add(make_kanji_collection(user.id, "one"))
    two = repo.add(make_kanji_collection(user.id, "two"))
    repo.add_item(one, items[0])
    repo.add_item(two, items[0])
    repo.add_item(two, items[1])
    repo.add_item(two, items[2])  # inactive

    assert repo.item_ids([one, two]) == {items[0].id, items[1].id}


def test_delete_keeps_the_items(
    session: Session,
    repo: SqlAlchemyKanjiCollectionRepository,
    user: UserORM,
    items: list[PracticeKanji],
) -> None:
    collection = repo.add(make_kanji_collection(user.id))
    repo.add_item(collection, items[0])
    repo.delete(collection)

    assert collection.id is not None
    assert items[0].id is not None
    assert repo.get(collection.id, user.id) is None
    assert repo.list_for_item(items[0]) == []
    assert (
        SqlAlchemyPracticeKanjiRepository(session).get(items[0].id, user.id) is not None
    )


def test_add_with_a_taken_name_fails_and_keeps_the_session_usable(
    repo: SqlAlchemyKanjiCollectionRepository, user: UserORM, other_user: UserORM
) -> None:
    kept = repo.add(make_kanji_collection(user.id, "same"))
    theirs = repo.add(make_kanji_collection(other_user.id, "same"))

    with pytest.raises(CollectionNameTakenError):
        repo.add(make_kanji_collection(user.id, "same"))

    assert theirs.name == "same"  # names are unique per user only
    assert repo.list_for_user(user.id) == [kept]


def test_update_to_a_taken_name_fails(
    repo: SqlAlchemyKanjiCollectionRepository, user: UserORM
) -> None:
    repo.add(make_kanji_collection(user.id, "a"))
    b = repo.add(make_kanji_collection(user.id, "b"))

    with pytest.raises(CollectionNameTakenError):
        repo.update(b.model_copy(update={"name": "a"}))

    assert b.id is not None
    assert repo.get(b.id, user.id) == b
