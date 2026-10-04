"""Read use cases over a user's saved exercises."""

from uuid import UUID

from ...domain.entities import Exercise
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import ExerciseRepository


class ListExercises:
    """The user's exercises, by name."""

    def __init__(self, exercises: ExerciseRepository) -> None:
        self._exercises = exercises

    def execute(self, user_id: UUID) -> list[Exercise]:
        return self._exercises.list_for_user(user_id)


class GetExercise:
    """One of the user's exercises; `EntityNotFoundError` otherwise."""

    def __init__(self, exercises: ExerciseRepository) -> None:
        self._exercises = exercises

    def execute(self, user_id: UUID, exercise_id: int) -> Exercise:
        exercise = self._exercises.get(exercise_id, user_id)
        if exercise is None:
            raise EntityNotFoundError(f"exercise {exercise_id} not found")
        return exercise
