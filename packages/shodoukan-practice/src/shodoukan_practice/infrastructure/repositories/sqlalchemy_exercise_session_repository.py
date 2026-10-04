from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ...domain.entities import ExerciseSession
from ...domain.exceptions import EntityNotFoundError, QuestionNotActiveError
from ...domain.repositories import ExerciseSessionRepository
from ..db.mappers import exercise_session_to_db, exercise_session_to_domain
from ..db.orm import ExerciseQuestionORM, ExerciseSessionORM


class SqlAlchemyExerciseSessionRepository(ExerciseSessionRepository):
    """Flushes but never commits: the caller owns the transaction.

    Writes to a session are serialized: `get_for_update` locks its row until
    the transaction ends, and `UNIQUE(session_id, position)` on its questions
    catches two writers asking the same next question anyway.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, session_id: int, user_id: UUID) -> ExerciseSession | None:
        row = self._session.scalars(self._select(session_id, user_id)).one_or_none()
        return exercise_session_to_domain(row) if row else None

    def get_for_update(self, session_id: int, user_id: UUID) -> ExerciseSession | None:
        """`get`, locking the session's row (`SELECT ... FOR UPDATE`) so a
        concurrent request on it waits for this transaction and then reads
        what it stored. SQLite has no row locks and ignores it."""
        query = self._select(session_id, user_id).with_for_update(of=ExerciseSessionORM)
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
        """Store the session's answers (and anything else changed in it).

        Raises `QuestionNotActiveError` if another request stored a question
        at the position of this one's new active question (the session
        changed meanwhile); only the savepoint is rolled back.
        """
        stored = (
            self._session.get(ExerciseSessionORM, session.id) if session.id else None
        )
        if stored is None or stored.user_id != session.user_id:
            raise EntityNotFoundError(f"exercise session {session.id} not found")
        try:
            with self._session.begin_nested():
                row = self._session.merge(exercise_session_to_db(session))
                self._session.flush()
        except IntegrityError:
            if not self._position_taken(session):
                raise
            raise QuestionNotActiveError(
                f"exercise session {session.id} changed meanwhile; reload it"
            ) from None
        return exercise_session_to_domain(row)

    def _position_taken(self, session: ExerciseSession) -> bool:
        """Whether a stored question other than the session's active one
        holds its position."""
        current = session.current
        if current is None:
            return False
        query = select(ExerciseQuestionORM.id).where(
            ExerciseQuestionORM.session_id == session.id,
            ExerciseQuestionORM.position == current.position,
        )
        if current.id is not None:
            query = query.where(ExerciseQuestionORM.id != current.id)
        return self._session.scalar(query) is not None

    def _select(self, session_id: int, user_id: UUID) -> Select[ExerciseSessionORM]:
        return (
            select(ExerciseSessionORM)
            .where(
                ExerciseSessionORM.id == session_id,
                ExerciseSessionORM.user_id == user_id,
            )
            .options(selectinload(ExerciseSessionORM.questions))
        )
