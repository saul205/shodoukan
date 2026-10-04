from datetime import timedelta

import pytest
from factories import NOW, make_kanji, make_kanji_collection
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import PracticeReadingItem
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeKanjiRepository,
)


@pytest.fixture
def repo(session: Session) -> SqlAlchemyPracticeKanjiRepository:
    return SqlAlchemyPracticeKanjiRepository(session)


def test_add_then_get(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, session: Session
) -> None:
    added = repo.add(make_kanji(user.id))
    session.expunge_all()

    assert added.id is not None
    assert repo.get(added.id, user.id) == added


def test_get_is_scoped_to_the_owner(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, other_user: UserORM
) -> None:
    added = repo.add(make_kanji(user.id))
    assert added.id is not None
    assert repo.get(added.id, other_user.id) is None


def test_get_many_skips_other_users(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, other_user: UserORM
) -> None:
    mine = repo.add(make_kanji(user.id, "食"))
    theirs = repo.add(make_kanji(other_user.id, "水"))
    ids = [k.id for k in (mine, theirs) if k.id is not None]

    assert repo.get_many(ids, user.id) == [mine]


def test_update_toggles_and_adds_readings(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, session: Session
) -> None:
    kanji = repo.add(make_kanji(user.id))
    kanji.kun_readings[1].enabled = False
    kanji.nanori.append(PracticeReadingItem(id=None, text="あき"))

    repo.update(kanji)
    session.expunge_all()
    assert kanji.id is not None
    stored = repo.get(kanji.id, user.id)

    assert stored is not None
    assert [(r.text, r.enabled) for r in stored.kun_readings] == [
        ("た.べる", True),
        ("く.う", False),
    ]
    assert [r.text for r in stored.nanori] == ["あき"]


def test_update_cannot_move_kanji_to_another_user(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, other_user: UserORM
) -> None:
    kanji = repo.add(make_kanji(user.id))
    with pytest.raises(EntityNotFoundError):
        repo.update(kanji.model_copy(update={"user_id": other_user.id}))


def test_get_by_literal_is_scoped_to_the_owner(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, other_user: UserORM
) -> None:
    added = repo.add(make_kanji(user.id))

    assert repo.get_by_literal("食", user.id) == added
    assert repo.get_by_literal("食", other_user.id) is None


def test_add_if_absent_creates_once(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, session: Session
) -> None:
    first, created = repo.add_if_absent(make_kanji(user.id))
    again, created_again = repo.add_if_absent(make_kanji(user.id))

    assert created is True
    assert created_again is False
    assert again == first
    # The failed insert only rolled back its savepoint: the session still works.
    session.commit()
    assert first.id is not None
    assert repo.get(first.id, user.id) == first


def test_practice_ids_by_literal_lists_only_the_users_imports(
    repo: SqlAlchemyPracticeKanjiRepository,
    user: UserORM,
    other_user: UserORM,
) -> None:
    mine = repo.add(make_kanji(user.id, "食"))
    repo.add(make_kanji(other_user.id, "水"))

    found = repo.practice_ids_by_literal(["食", "水", "龘"], user.id)

    assert found == {"食": mine.id}


def test_list_for_user_is_newest_first_and_paginated(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, other_user: UserORM
) -> None:
    old = repo.add(make_kanji(user.id, "一"))
    new = repo.add(
        make_kanji(user.id, "二").model_copy(update={"created_at": NOW + timedelta(1)})
    )
    same_time_later_id = repo.add(make_kanji(user.id, "三"))
    repo.add(make_kanji(other_user.id, "一"))

    assert repo.list_for_user(user.id, limit=10, offset=0) == [
        new,
        same_time_later_id,
        old,
    ]
    assert repo.list_for_user(user.id, limit=1, offset=1) == [same_time_later_id]
    assert repo.count_for_user(user.id) == 3


def test_list_for_user_filters_by_active(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM
) -> None:
    active = repo.add(make_kanji(user.id, "一"))
    inactive = repo.add(make_kanji(user.id, "二", is_active=False))

    assert repo.list_for_user(user.id, 10, 0, active=True) == [active]
    assert repo.list_for_user(user.id, 10, 0, active=False) == [inactive]
    assert repo.count_for_user(user.id, active=False) == 1


def test_count_for_user_without_items_is_zero(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM
) -> None:
    assert repo.count_for_user(user.id) == 0


def test_delete_removes_the_item_and_its_links(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyKanjiCollectionRepository(session)
    collection = collections.add(make_kanji_collection(user.id))
    item = repo.add(make_kanji(user.id))
    collections.add_item(collection, item)
    assert item.id is not None

    repo.delete(item)

    assert repo.get(item.id, user.id) is None
    assert collections.item_ids([collection]) == set()
    assert collections.get(collection.id or 0, user.id) == collection


def test_delete_of_another_users_item_fails(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, other_user: UserORM
) -> None:
    item = repo.add(make_kanji(user.id))
    with pytest.raises(EntityNotFoundError):
        repo.delete(item.model_copy(update={"user_id": other_user.id}))
    assert item.id is not None
    assert repo.get(item.id, user.id) is not None


def test_count_by_collection_filters_by_active(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyKanjiCollectionRepository(session)
    collection = collections.add(make_kanji_collection(user.id))
    collections.add_item(collection, repo.add(make_kanji(user.id, "一")))
    collections.add_item(
        collection, repo.add(make_kanji(user.id, "二", is_active=False))
    )

    assert repo.count_by_collection(collection) == 2
    assert repo.count_by_collection(collection, active=True) == 1
    assert repo.count_by_collection(collection, active=False) == 1
