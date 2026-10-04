"""Port for exercise sessions: the questions asked and the answers given."""

from typing import Protocol
from uuid import UUID

from ..entities import ExerciseSession


class ExerciseSessionRepository(Protocol):
    def get(self, session_id: int, user_id: UUID) -> ExerciseSession | None: ...

    def list_open(self, user_id: UUID, exercise_id: int) -> list[ExerciseSession]:
        """The user's sessions of that exercise that aren't finished."""
        ...

    def add(self, session: ExerciseSession) -> ExerciseSession:
        """Store a new session; its questions get their ids."""
        ...

    def update(self, session: ExerciseSession) -> ExerciseSession:
        """Store its questions, answers and state; a dropped active question is
        deleted. Raises `EntityNotFoundError` for a missing or foreign session."""
        ...
