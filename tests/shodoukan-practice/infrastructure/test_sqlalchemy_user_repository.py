from uuid import uuid4

from factories import NOW
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import User
from shodoukan_practice.infrastructure.repositories import SqlAlchemyUserRepository


def test_add_then_get(session: Session) -> None:
    repo = SqlAlchemyUserRepository(session)
    user_id = uuid4()
    added = repo.add(User(id=user_id, username="kana", created_at=NOW, updated_at=NOW))

    assert added.id == user_id
    assert repo.get(user_id) == added


def test_get_missing_user(session: Session) -> None:
    assert SqlAlchemyUserRepository(session).get(uuid4()) is None


def test_add_if_absent_creates_once(session: Session) -> None:
    repo = SqlAlchemyUserRepository(session)
    user_id = uuid4()
    first, created = repo.add_if_absent(User(id=user_id, username="k"))
    again, created_again = repo.add_if_absent(User(id=user_id, username="other name"))

    assert created is True
    assert created_again is False
    assert again == first
    # Only the savepoint was rolled back: the session still works.
    session.commit()
    assert repo.get(user_id) == first


def test_usernames_needn_t_be_unique(session: Session) -> None:
    repo = SqlAlchemyUserRepository(session)
    repo.add(User(id=uuid4(), username="kana"))
    repo.add(User(id=uuid4(), username="kana"))
    session.flush()
