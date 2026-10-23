"""Port for statistics over the answers of exercise sessions.

Sessions are the statistics: every figure is an aggregate over the answered
questions (their snapshot columns), computed when asked; nothing is stored
twice. The results are frozen read models, not aggregates. Every method is
scoped to the user, and to one exercise when one is given.
"""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..entities import Exercise, ItemKind, StudyField


class _ReadModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class AnswerTotals(_ReadModel):
    sessions: int  # sessions with at least one answer
    answered: int
    correct: int
    mean_response_ms: float | None  # None if no answer measured the time


class DirectionTotals(_ReadModel):
    """Answers to one direction. The shown fields are a set: a direction is the
    same whatever their order."""

    prompt_fields: frozenset[StudyField]
    answer_field: StudyField
    answered: int
    correct: int


class ItemTotals(_ReadModel):
    """Answers about one item (an entry or a kanji, per the method asked)."""

    item_id: int
    answered: int
    wrong: int


class ExerciseTotals(_ReadModel):
    """Answers to one exercise that still exists, under its current name."""

    exercise_id: int
    exercise_name: str
    item_kind: ItemKind
    sessions: int
    answered: int
    correct: int
    last_answered_at: datetime


class AnswerMoment(_ReadModel):
    answered_at: datetime
    is_correct: bool


class ExerciseStatisticsRepository(Protocol):
    def totals(self, user_id: UUID, exercise: Exercise | None = None) -> AnswerTotals:
        """Over every session of the user, or of `exercise`."""
        ...

    def by_direction(
        self, user_id: UUID, exercise: Exercise | None = None
    ) -> list[DirectionTotals]:
        """One row per direction asked, most answered first."""
        ...

    def most_missed_entries(
        self, user_id: UUID, exercise: Exercise | None = None, limit: int = 10
    ) -> list[ItemTotals]:
        """Entries answered wrong at least once, most misses first (then fewest
        answers). Questions whose entry left the library don't count."""
        ...

    def most_missed_kanji(
        self, user_id: UUID, exercise: Exercise | None = None, limit: int = 10
    ) -> list[ItemTotals]:
        """`most_missed_entries` for kanji."""
        ...

    def by_exercise(self, user_id: UUID) -> list[ExerciseTotals]:
        """One row per exercise with answers, most recently answered first.
        Sessions of deleted exercises aren't listed."""
        ...

    def answers_since(self, user_id: UUID, since: datetime) -> list[AnswerMoment]:
        """When each answer since `since` was given and whether it was right,
        oldest first."""
        ...
