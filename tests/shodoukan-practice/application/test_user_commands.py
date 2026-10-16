from uuid import uuid4

from factories import NOW, USER_ID
from sqlalchemy.orm import Session

from shodoukan_practice.application.commands import EnsureUser
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import SqlAlchemyUserRepository


def test_known_identity_returns_its_user(session: Session, user: UserORM) -> None:
    found = EnsureUser(SqlAlchemyUserRepository(session)).execute(USER_ID, "saul")

    assert found.id == user.id
    assert found.username == "saul"
    assert found.updated_at == user.updated_at


def test_known_identity_takes_the_providers_new_name(
    session: Session, user: UserORM
) -> None:
    users = SqlAlchemyUserRepository(session)
    EnsureUser(users).execute(USER_ID, "saul205")
    session.expunge_all()

    stored = users.get(USER_ID)
    assert stored is not None
    assert stored.username == "saul205"
    assert stored.updated_at > NOW


def test_a_token_without_a_name_keeps_the_stored_one(
    session: Session, user: UserORM
) -> None:
    found = EnsureUser(SqlAlchemyUserRepository(session)).execute(USER_ID, None)
    assert found.username == "saul"
    created = EnsureUser(SqlAlchemyUserRepository(session)).execute(uuid4(), None)
    assert created.username == str(created.id)


def test_new_identity_creates_its_user_with_the_provider_id(session: Session) -> None:
    users = SqlAlchemyUserRepository(session)
    provider_id = uuid4()

    created = EnsureUser(users).execute(provider_id, "newbie")

    assert created.id == provider_id
    assert created.username == "newbie"
    assert users.get(provider_id) == created


def test_same_identity_twice_creates_one_user(session: Session) -> None:
    ensure = EnsureUser(SqlAlchemyUserRepository(session))
    provider_id = uuid4()

    first = ensure.execute(provider_id, "newbie")
    again = ensure.execute(provider_id, "newbie")

    assert again == first
