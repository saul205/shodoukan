from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...domain.entities import User
from ...domain.repositories import UserRepository
from ..db.mappers import user_to_db, user_to_domain
from ..db.orm import UserORM


class SqlAlchemyUserRepository(UserRepository):
    """Flushes but never commits: the caller owns the transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: UUID) -> User | None:
        row = self._session.get(UserORM, user_id)
        return user_to_domain(row) if row else None

    def add_if_absent(self, user: User) -> tuple[User, bool]:
        row = user_to_db(user)
        try:
            # Savepoint: a concurrent first request for the same user
            # (primary-key clash) rolls back only this insert.
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError:
            existing = self.get(user.id)
            if existing is None:
                raise
            return existing, False
        return user_to_domain(row), True

    def add(self, user: User) -> User:
        row = user_to_db(user)
        self._session.add(row)
        self._session.flush()
        return user_to_domain(row)
