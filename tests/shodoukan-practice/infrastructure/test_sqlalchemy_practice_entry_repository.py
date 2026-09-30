import pytest
from factories import make_entry
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import PracticeGloss
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
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
