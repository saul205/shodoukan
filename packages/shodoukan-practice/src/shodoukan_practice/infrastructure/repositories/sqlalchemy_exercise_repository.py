from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...domain.entities import Exercise
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import ExerciseRepository
from ..db.mappers import exercise_to_db, exercise_to_domain
from ..db.orm import ExerciseORM

_LOAD_LINKS = (
    selectinload(ExerciseORM.entry_collections),
    selectinload(ExerciseORM.kanji_collections),
)


class SqlAlchemyExerciseRepository(ExerciseRepository):
    """Flushes but never commits: the caller owns the transaction.

    The collection links are child rows of the exercise, so `update` adds and
    removes them through `merge` like any nested item.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, exercise_id: int, user_id: UUID) -> Exercise | None:
        query = (
            select(ExerciseORM)
            .where(ExerciseORM.id == exercise_id, ExerciseORM.user_id == user_id)
            .options(*_LOAD_LINKS)
        )
        row = self._session.scalars(query).one_or_none()
        return exercise_to_domain(row) if row else None

    def list_for_user(self, user_id: UUID) -> list[Exercise]:
        query = (
            select(ExerciseORM)
            .where(ExerciseORM.user_id == user_id)
            .order_by(ExerciseORM.name, ExerciseORM.id)
            .options(*_LOAD_LINKS)
        )
        return [exercise_to_domain(row) for row in self._session.scalars(query)]

    def add(self, exercise: Exercise) -> Exercise:
        row = exercise_to_db(exercise)
        self._session.add(row)
        self._session.flush()
        return exercise_to_domain(row)

    def update(self, exercise: Exercise) -> Exercise:
        """Replace the stored exercise and its collection links."""
        self._require_row(exercise)
        row = self._session.merge(exercise_to_db(exercise))
        self._session.flush()
        return exercise_to_domain(row)

    def delete(self, exercise: Exercise) -> None:
        """Delete the exercise and its links; the collections stay."""
        self._session.delete(self._require_row(exercise))
        self._session.flush()

    def _require_row(self, exercise: Exercise) -> ExerciseORM:
        row = self._session.get(ExerciseORM, exercise.id) if exercise.id else None
        if row is None or row.user_id != exercise.user_id:
            raise EntityNotFoundError(f"exercise {exercise.id} not found")
        return row
