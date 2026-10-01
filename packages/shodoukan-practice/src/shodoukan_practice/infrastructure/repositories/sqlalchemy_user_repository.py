from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.entities import User
from ...domain.repositories import UserRepository
from ..db.mappers import user_to_db, user_to_domain
from ..db.orm import UserORM


class SqlAlchemyUserRepository(UserRepository):
    """Flushes but never commits: the caller owns the transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: int) -> User | None:
        row = self._session.get(UserORM, user_id)
        return user_to_domain(row) if row else None

    def get_by_subject(self, subject: str) -> User | None:
        row = self._session.scalars(
            select(UserORM).where(UserORM.subject == subject)
        ).one_or_none()
        return user_to_domain(row) if row else None

    def add(self, user: User) -> User:
        row = user_to_db(user)
        self._session.add(row)
        self._session.flush()
        return user_to_domain(row)
