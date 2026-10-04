"""Port for exercise sessions: the questions asked and the answers given."""

from typing import Protocol
from uuid import UUID

from ..entities import ExerciseSession


class ExerciseSessionRepository(Protocol):
    def get(self, session_id: int, user_id: UUID) -> ExerciseSession | None: ...

    def add(self, session: ExerciseSession) -> ExerciseSession:
        """Store a new session; its questions get their ids."""
        ...

    def update(self, session: ExerciseSession) -> ExerciseSession:
        """Store the answers given. Raises `EntityNotFoundError` for a missing or
        foreign session."""
        ...
