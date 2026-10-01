import pytest
from sqlalchemy.orm import Session

from shodoukan_practice.application.queries import GetRegisteredUser
from shodoukan_practice.domain.exceptions import UserNotRegisteredError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import SqlAlchemyUserRepository


def test_registered_user_is_found(session: Session, user: UserORM) -> None:
    found = GetRegisteredUser(SqlAlchemyUserRepository(session)).execute("sub-saul")
    assert found.id == user.id


def test_unknown_subject_is_rejected(session: Session, user: UserORM) -> None:
    query = GetRegisteredUser(SqlAlchemyUserRepository(session))
    with pytest.raises(UserNotRegisteredError):
        query.execute("sub-nobody")
