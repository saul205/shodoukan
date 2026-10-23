"""Port for a user's saved exercises, with the collections they draw from."""

from typing import Protocol
from uuid import UUID

from ..entities import Exercise


class ExerciseRepository(Protocol):
    def get(self, exercise_id: int, user_id: UUID) -> Exercise | None: ...

    def list_for_user(self, user_id: UUID) -> list[Exercise]:
        """The user's exercises, by name."""
        ...

    def add(self, exercise: Exercise) -> Exercise: ...

    def update(self, exercise: Exercise) -> Exercise:
        """Raises `EntityNotFoundError` for a missing or foreign exercise."""
        ...

    def delete(self, exercise: Exercise) -> None: ...
