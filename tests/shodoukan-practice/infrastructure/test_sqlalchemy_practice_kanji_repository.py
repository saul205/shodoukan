import pytest
from factories import make_kanji
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import PracticeReadingItem
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
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
