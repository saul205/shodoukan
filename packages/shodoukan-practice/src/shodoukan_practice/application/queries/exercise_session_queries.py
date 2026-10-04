"""Read use cases over exercise sessions."""

from uuid import UUID

from ...domain.entities import ExerciseSession
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import ExerciseSessionRepository


class GetExerciseSession:
    """One of the user's sessions, to play on or review."""

    def __init__(self, sessions: ExerciseSessionRepository) -> None:
        self._sessions = sessions

    def execute(self, user_id: UUID, session_id: int) -> ExerciseSession:
        session = self._sessions.get(session_id, user_id)
        if session is None:
            raise EntityNotFoundError(f"exercise session {session_id} not found")
        return session
