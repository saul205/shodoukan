"""Port for exercise sessions: the questions asked and the answers given.

Besides whole sessions, it lists `SessionSummary` read models for the
history: a session's figures without its questions.
"""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..entities import ExerciseSession, ItemKind, SessionStatus, session_end


class SessionSummary(BaseModel):
    """A session as the history lists it: no questions, just its figures."""

    model_config = ConfigDict(frozen=True)

    id: int
    exercise_id: int | None
    exercise_name: str
    item_kind: ItemKind
    started_at: datetime
    last_activity_at: datetime
    finished_at: datetime | None  # as stored; see `ended_at`
    answered: int
    score: int

    def ended_at(self, now: datetime) -> datetime | None:
        """When it ended, idle sessions included, as `ExerciseSession.ended_at`."""
        return session_end(self.finished_at, self.last_activity_at, now)


class ExerciseSessionRepository(Protocol):
    def get(self, session_id: int, user_id: UUID) -> ExerciseSession | None: ...

    def get_for_update(self, session_id: int, user_id: UUID) -> ExerciseSession | None:
        """`get`, locking the session until the transaction ends, for the use
        cases that change it: concurrent answers are serialized."""
        ...

    def list_open(self, user_id: UUID) -> list[ExerciseSession]:
        """The user's sessions with no `finished_at` (at most one, normally),
        locked until the transaction ends so they can be closed safely.

        Some may be idle: an idle session isn't written until it's closed (see
        `ExerciseSession.ended_at`)."""
        ...

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
        """The user's sessions, newest first, optionally of one exercise and
        only open or only ended ones at `now` (idle ones count as ended)."""
        ...

    def count_summaries(
        self,
        user_id: UUID,
        now: datetime,
        *,
        exercise_id: int | None = None,
        status: SessionStatus | None = None,
    ) -> int:
        """How many sessions `list_summaries` would list across every page."""
        ...

    def add(self, session: ExerciseSession) -> ExerciseSession:
        """Store a new session; its questions get their ids. Raises
        `SessionAlreadyOpenError` if the user has another open session."""
        ...

    def update(self, session: ExerciseSession) -> ExerciseSession:
        """Store its questions, answers and state; a dropped active question is
        deleted. Raises `EntityNotFoundError` for a missing or foreign session,
        and `QuestionNotActiveError` if it changed meanwhile."""
        ...
