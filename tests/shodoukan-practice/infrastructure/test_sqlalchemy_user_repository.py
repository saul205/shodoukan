from factories import NOW
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import User
from shodoukan_practice.infrastructure.repositories import SqlAlchemyUserRepository


def test_add_then_get(session: Session) -> None:
    repo = SqlAlchemyUserRepository(session)
    added = repo.add(User(id=None, username="kana", created_at=NOW, updated_at=NOW))

    assert added.id is not None
    assert repo.get(added.id) == added


def test_get_missing_user(session: Session) -> None:
    assert SqlAlchemyUserRepository(session).get(999) is None
