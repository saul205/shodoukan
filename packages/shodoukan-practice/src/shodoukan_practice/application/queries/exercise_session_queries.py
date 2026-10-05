"""Read use cases over exercise sessions."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ...domain.entities import ExerciseSession, SessionStatus
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import ExerciseSessionRepository, SessionSummary


@dataclass(frozen=True)
class SessionSummaryPage:
    """A page of the user's session history, and how many sessions match."""

    items: list[SessionSummary]
    total: int
    limit: int
    offset: int


class GetExerciseSession:
    """One of the user's sessions, to play on or review."""

    def __init__(self, sessions: ExerciseSessionRepository) -> None:
        self._sessions = sessions

    def execute(self, user_id: UUID, session_id: int) -> ExerciseSession:
        session = self._sessions.get(session_id, user_id)
        if session is None:
            raise EntityNotFoundError(f"exercise session {session_id} not found")
        return session


class ListExerciseSessions:
    """The user's session history, newest first.

    `exercise_id` filters by exercise without checking it exists: sessions
    outlive their exercise, so a deleted one just lists nothing new.
    `status="open"` finds the session to resume (at most one is open);
    whether a session is open is decided at `now`, idle ones counting as
    ended.
    """

    def __init__(self, sessions: ExerciseSessionRepository) -> None:
        self._sessions = sessions

    def execute(
        self,
        user_id: UUID,
        now: datetime,
        *,
        exercise_id: int | None = None,
        status: SessionStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SessionSummaryPage:
        items = self._sessions.list_summaries(
            user_id,
            now,
            exercise_id=exercise_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        total = self._sessions.count_summaries(
            user_id, now, exercise_id=exercise_id, status=status
        )
        return SessionSummaryPage(items=items, total=total, limit=limit, offset=offset)
