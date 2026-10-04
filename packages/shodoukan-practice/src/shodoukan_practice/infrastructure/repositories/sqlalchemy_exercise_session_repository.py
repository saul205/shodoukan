from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...domain.entities import ExerciseSession
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import ExerciseSessionRepository
from ..db.mappers import exercise_session_to_db, exercise_session_to_domain
from ..db.orm import ExerciseSessionORM


class SqlAlchemyExerciseSessionRepository(ExerciseSessionRepository):
    """Flushes but never commits: the caller owns the transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, session_id: int, user_id: UUID) -> ExerciseSession | None:
        query = (
            select(ExerciseSessionORM)
            .where(
                ExerciseSessionORM.id == session_id,
                ExerciseSessionORM.user_id == user_id,
            )
            .options(selectinload(ExerciseSessionORM.questions))
        )
        row = self._session.scalars(query).one_or_none()
        return exercise_session_to_domain(row) if row else None

    def list_open(self, user_id: UUID, exercise_id: int) -> list[ExerciseSession]:
        query = (
            select(ExerciseSessionORM)
            .where(
                ExerciseSessionORM.user_id == user_id,
                ExerciseSessionORM.exercise_id == exercise_id,
                ExerciseSessionORM.finished_at.is_(None),
            )
            .order_by(ExerciseSessionORM.id)
            .options(selectinload(ExerciseSessionORM.questions))
        )
        return [exercise_session_to_domain(row) for row in self._session.scalars(query)]

    def add(self, session: ExerciseSession) -> ExerciseSession:
        row = exercise_session_to_db(session)
        self._session.add(row)
        self._session.flush()
        return exercise_session_to_domain(row)

    def update(self, session: ExerciseSession) -> ExerciseSession:
        """Store the session's answers (and anything else changed in it)."""
        stored = (
            self._session.get(ExerciseSessionORM, session.id) if session.id else None
        )
        if stored is None or stored.user_id != session.user_id:
            raise EntityNotFoundError(f"exercise session {session.id} not found")
        row = self._session.merge(exercise_session_to_db(session))
        self._session.flush()
        return exercise_session_to_domain(row)
