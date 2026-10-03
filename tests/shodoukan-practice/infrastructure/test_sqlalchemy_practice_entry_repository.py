from datetime import timedelta

import pytest
from factories import NOW, make_entry, make_entry_collection
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import PracticeGloss
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
)


@pytest.fixture
def repo(session: Session) -> SqlAlchemyPracticeEntryRepository:
    return SqlAlchemyPracticeEntryRepository(session)


def test_add_assigns_ids_and_get_returns_it(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    added = repo.add(make_entry(user.id))
    session.expunge_all()

    assert added.id is not None
    assert all(g.id is not None for g in added.senses[0].glosses)
    assert repo.get(added.id, user.id) == added


def test_get_is_scoped_to_the_owner(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    added = repo.add(make_entry(user.id))
    assert added.id is not None
    assert repo.get(added.id, other_user.id) is None


def test_get_many_skips_other_users(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    mine = repo.add(make_entry(user.id, 1))
    theirs = repo.add(make_entry(other_user.id, 2))
    ids = [e.id for e in (mine, theirs) if e.id is not None]

    assert repo.get_many(ids, user.id) == [mine]


def test_update_edits_adds_and_removes_nested_items(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    entry = repo.add(make_entry(user.id))
    glosses = entry.senses[0].glosses
    glosses[0].enabled = False
    del glosses[1]
    glosses.append(
        PracticeGloss(id=None, text="to dine", lang="eng", type=None, origin="added")
    )

    updated = repo.update(entry)
    session.expunge_all()
    assert entry.id is not None
    stored = repo.get(entry.id, user.id)

    assert stored == updated
    assert stored is not None
    texts = [(g.text, g.enabled, g.origin) for g in stored.senses[0].glosses]
    assert texts == [("to eat", False, "imported"), ("to dine", True, "added")]


def test_update_cannot_move_an_entry_to_another_user(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    entry = repo.add(make_entry(user.id))
    stolen = entry.model_copy(update={"user_id": other_user.id})

    with pytest.raises(EntityNotFoundError):
        repo.update(stolen)


def test_update_of_unsaved_entry_fails(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    with pytest.raises(EntityNotFoundError):
        repo.update(make_entry(user.id))


def test_get_by_source_entry_id_is_scoped_to_the_owner(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    added = repo.add(make_entry(user.id))

    assert repo.get_by_source_entry_id(1000001, user.id) == added
    assert repo.get_by_source_entry_id(1000001, other_user.id) is None


def test_add_if_absent_creates_once(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    first, created = repo.add_if_absent(make_entry(user.id))
    again, created_again = repo.add_if_absent(make_entry(user.id))

    assert created is True
    assert created_again is False
    assert again == first
    # The failed insert only rolled back its savepoint: the session still works.
    session.commit()
    assert first.id is not None
    assert repo.get(first.id, user.id) == first


def test_practice_ids_by_source_entry_id_lists_only_the_users_imports(
    repo: SqlAlchemyPracticeEntryRepository,
    user: UserORM,
    other_user: UserORM,
) -> None:
    mine = repo.add(make_entry(user.id, 1000001))
    repo.add(make_entry(other_user.id, 1000002))

    found = repo.practice_ids_by_source_entry_id([1000001, 1000002, 999], user.id)

    assert found == {1000001: mine.id}


def test_list_for_user_is_newest_first_and_paginated(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    old = repo.add(make_entry(user.id, 1))
    new = repo.add(
        make_entry(user.id, 2).model_copy(update={"created_at": NOW + timedelta(1)})
    )
    same_time_later_id = repo.add(make_entry(user.id, 3))
    repo.add(make_entry(other_user.id, 1))

    assert repo.list_for_user(user.id, limit=10, offset=0) == [
        new,
        same_time_later_id,
        old,
    ]
    assert repo.list_for_user(user.id, limit=1, offset=1) == [same_time_later_id]
    assert repo.count_for_user(user.id) == 3


def test_list_for_user_filters_by_active(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    active = repo.add(make_entry(user.id, 1))
    inactive = repo.add(make_entry(user.id, 2, is_active=False))

    assert repo.list_for_user(user.id, 10, 0, active=True) == [active]
    assert repo.list_for_user(user.id, 10, 0, active=False) == [inactive]
    assert repo.count_for_user(user.id, active=False) == 1


def test_count_for_user_without_items_is_zero(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    assert repo.count_for_user(user.id) == 0


def test_delete_removes_the_item_and_its_links(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyEntryCollectionRepository(session)
    collection = collections.add(make_entry_collection(user.id))
    item = repo.add(make_entry(user.id))
    collections.add_item(collection, item)
    assert item.id is not None

    repo.delete(item)

    assert repo.get(item.id, user.id) is None
    assert collections.item_ids([collection]) == set()
    assert collections.get(collection.id or 0, user.id) == collection


def test_delete_of_another_users_item_fails(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    item = repo.add(make_entry(user.id))
    with pytest.raises(EntityNotFoundError):
        repo.delete(item.model_copy(update={"user_id": other_user.id}))
    assert item.id is not None
    assert repo.get(item.id, user.id) is not None


def test_count_by_collection_counts_active_items(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyEntryCollectionRepository(session)
    collection = collections.add(make_entry_collection(user.id))
    collections.add_item(collection, repo.add(make_entry(user.id, 1)))
    collections.add_item(collection, repo.add(make_entry(user.id, 2, is_active=False)))

    assert repo.count_by_collection(collection) == 1


def test_update_persists_added_edited_and_removed_meanings(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    entry = repo.add(make_entry(user.id))
    sense_id = entry.senses[0].id
    assert sense_id is not None

    entry.add_gloss(sense_id, "to scoff", "eng")
    entry = repo.update(entry)
    added = entry.senses[0].glosses[-1]
    assert added.id is not None and added.origin == "added"

    entry.edit_gloss(added.id, "to wolf down")
    entry.set_sense_notes(sense_id, "casual")
    entry = repo.update(entry)
    session.expunge_all()
    stored = repo.get(entry.id or 0, user.id)
    assert stored is not None
    assert stored.senses[0].glosses[-1].text == "to wolf down"
    assert stored.senses[0].notes == "casual"

    stored.remove_gloss(added.id)
    repo.update(stored)
    session.expunge_all()
    reloaded = repo.get(entry.id or 0, user.id)
    assert reloaded is not None
    assert [g.origin for g in reloaded.senses[0].glosses] == ["imported", "imported"]
