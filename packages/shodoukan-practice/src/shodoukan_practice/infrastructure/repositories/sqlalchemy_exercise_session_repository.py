from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ...domain.entities import IDLE_TIMEOUT, ExerciseSession, SessionStatus
from ...domain.exceptions import (
    EntityNotFoundError,
    QuestionNotActiveError,
    SessionAlreadyOpenError,
)
from ...domain.repositories import ExerciseSessionRepository, SessionSummary
from ..db.mappers import exercise_session_to_db, exercise_session_to_domain
from ..db.orm import ExerciseQuestionORM, ExerciseSessionORM


class SqlAlchemyExerciseSessionRepository(ExerciseSessionRepository):
    """Flushes but never commits: the caller owns the transaction.

    Writes to a session are serialized: `get_for_update` and `list_open` lock
    its row until the transaction ends, and `UNIQUE(session_id, position)` on
    its questions catches two writers asking the same next question anyway. A
    partial unique index keeps one open session per user.
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

    def list_open(self, user_id: UUID) -> list[ExerciseSession]:
        query = (
            select(ExerciseSessionORM)
            .where(
                ExerciseSessionORM.user_id == user_id,
                ExerciseSessionORM.finished_at.is_(None),
            )
            .order_by(ExerciseSessionORM.id)
            .options(selectinload(ExerciseSessionORM.questions))
            .with_for_update(of=ExerciseSessionORM)
        )
        return [exercise_session_to_domain(row) for row in self._session.scalars(query)]

    def list_summaries(
        self,
        user_id: UUID,
        now: datetime,
        *,
        exercise_id: int | None = None,
        status: SessionStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SessionSummary]:
        """Counts come from correlated subqueries over the questions, so no
        question is loaded."""
        answered = (
            select(func.count())
            .where(
                ExerciseQuestionORM.session_id == ExerciseSessionORM.id,
                ExerciseQuestionORM.answered_at.is_not(None),
            )
            .correlate(ExerciseSessionORM)
            .scalar_subquery()
        )
        score = (
            select(func.count())
            .where(
                ExerciseQuestionORM.session_id == ExerciseSessionORM.id,
                ExerciseQuestionORM.is_correct.is_(True),
            )
            .correlate(ExerciseSessionORM)
            .scalar_subquery()
        )
        query = (
            select(ExerciseSessionORM, answered, score)
            .where(*self._summary_filters(user_id, now, exercise_id, status))
            .order_by(
                ExerciseSessionORM.created_at.desc(), ExerciseSessionORM.id.desc()
            )
            .limit(limit)
            .offset(offset)
        )
        return [
            SessionSummary(
                id=row.id,
                exercise_id=row.exercise_id,
                exercise_name=row.exercise_name,
                item_kind=row.item_kind,
                started_at=row.created_at,
                last_activity_at=row.updated_at,
                finished_at=row.finished_at,
                answered=answered_count,
                score=right,
            )
            for row, answered_count, right in self._session.execute(query)
        ]

    def count_summaries(
        self,
        user_id: UUID,
        now: datetime,
        *,
        exercise_id: int | None = None,
        status: SessionStatus | None = None,
    ) -> int:
        query = select(func.count(ExerciseSessionORM.id)).where(
            *self._summary_filters(user_id, now, exercise_id, status)
        )
        return self._session.scalar(query) or 0

    def add(self, session: ExerciseSession) -> ExerciseSession:
        """Raises `SessionAlreadyOpenError` if the user has another open session
        (the partial unique index); only the savepoint is rolled back."""
        row = exercise_session_to_db(session)
        try:
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError:
            if session.is_finished or not self._has_open(session.user_id):
                raise
            raise SessionAlreadyOpenError(
                "another exercise session was started meanwhile"
            ) from None
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

    @staticmethod
    def _summary_filters(
        user_id: UUID,
        now: datetime,
        exercise_id: int | None,
        status: SessionStatus | None,
    ) -> list[ColumnElement[bool]]:
        """Open is `ExerciseSession.ended_at(now) is None` in SQL: not closed,
        and active within `IDLE_TIMEOUT`."""
        filters: list[ColumnElement[bool]] = [ExerciseSessionORM.user_id == user_id]
        if exercise_id is not None:
            filters.append(ExerciseSessionORM.exercise_id == exercise_id)
        idle_since = now - IDLE_TIMEOUT
        if status == "open":
            filters += [
                ExerciseSessionORM.finished_at.is_(None),
                ExerciseSessionORM.updated_at >= idle_since,
            ]
        elif status == "finished":
            filters.append(
                or_(
                    ExerciseSessionORM.finished_at.is_not(None),
                    ExerciseSessionORM.updated_at < idle_since,
                )
            )
        return filters

    def _has_open(self, user_id: UUID) -> bool:
        query = select(ExerciseSessionORM.id).where(
            ExerciseSessionORM.user_id == user_id,
            ExerciseSessionORM.finished_at.is_(None),
        )
        return self._session.scalar(query) is not None

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
