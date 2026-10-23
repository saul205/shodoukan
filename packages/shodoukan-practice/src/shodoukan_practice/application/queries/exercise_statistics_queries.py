"""Statistics over the user's exercise sessions: per exercise and overall.

The figures are aggregates from the statistics port; these use cases add
what the user sees them with: the items' current names in the library, and
the answers per day in the user's time zone.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from ...domain.entities import Exercise
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import (
    AnswerTotals,
    DirectionTotals,
    ExerciseRepository,
    ExerciseStatisticsRepository,
    ExerciseTotals,
    ItemTotals,
    PracticeEntryRepository,
    PracticeKanjiRepository,
)
from ...domain.services import entry_label

# How many of the most missed items a statistics view lists.
MOST_MISSED_LIMIT = 10
# The longest window of daily activity that can be asked for.
MAX_ACTIVITY_DAYS = 365


@dataclass(frozen=True)
class MissedItem:
    """An item answered wrong, named as it is now in the library: a word by
    its usual form (and its reading), a kanji by itself."""

    item_id: int
    label: str
    reading: str | None
    answered: int
    wrong: int


@dataclass(frozen=True)
class DayActivity:
    day: date  # in the user's time zone
    answered: int
    correct: int


@dataclass(frozen=True)
class ExerciseStatistics:
    exercise: Exercise
    totals: AnswerTotals
    directions: list[DirectionTotals]
    most_missed: list[MissedItem]


@dataclass(frozen=True)
class PracticeStatistics:
    totals: AnswerTotals
    activity: list[DayActivity]  # every day of the window, oldest first
    exercises: list[ExerciseTotals]
    most_missed_entries: list[MissedItem]
    most_missed_kanji: list[MissedItem]


class _MissedItems:
    """Names the most missed items after the library; items that left it are
    left out."""

    def __init__(
        self, entries: PracticeEntryRepository, kanji: PracticeKanjiRepository
    ) -> None:
        self._entries = entries
        self._kanji = kanji

    def entries(self, user_id: UUID, totals: list[ItemTotals]) -> list[MissedItem]:
        found = {
            entry.id: entry
            for entry in self._entries.get_many([t.item_id for t in totals], user_id)
        }
        items = []
        for total in totals:
            entry = found.get(total.item_id)
            if entry is None:
                continue
            label, reading = entry_label(entry)
            items.append(_missed(total, label, reading))
        return items

    def kanji(self, user_id: UUID, totals: list[ItemTotals]) -> list[MissedItem]:
        found = {
            kanji.id: kanji
            for kanji in self._kanji.get_many([t.item_id for t in totals], user_id)
        }
        return [
            _missed(total, found[total.item_id].literal, None)
            for total in totals
            if total.item_id in found
        ]


def _missed(total: ItemTotals, label: str, reading: str | None) -> MissedItem:
    return MissedItem(
        item_id=total.item_id,
        label=label,
        reading=reading,
        answered=total.answered,
        wrong=total.wrong,
    )


class GetExerciseStatistics:
    """How the user does in one exercise: totals, accuracy per direction and
    the items they miss most. Raises `EntityNotFoundError` if the exercise
    isn't theirs."""

    def __init__(
        self,
        exercises: ExerciseRepository,
        statistics: ExerciseStatisticsRepository,
        entries: PracticeEntryRepository,
        kanji: PracticeKanjiRepository,
    ) -> None:
        self._exercises = exercises
        self._statistics = statistics
        self._missed = _MissedItems(entries, kanji)

    def execute(self, user_id: UUID, exercise_id: int) -> ExerciseStatistics:
        exercise = self._exercises.get(exercise_id, user_id)
        if exercise is None:
            raise EntityNotFoundError(f"exercise {exercise_id} not found")
        if exercise.item_kind == "entries":
            most_missed = self._missed.entries(
                user_id,
                self._statistics.most_missed_entries(
                    user_id, exercise, MOST_MISSED_LIMIT
                ),
            )
        else:
            most_missed = self._missed.kanji(
                user_id,
                self._statistics.most_missed_kanji(
                    user_id, exercise, MOST_MISSED_LIMIT
                ),
            )
        return ExerciseStatistics(
            exercise=exercise,
            totals=self._statistics.totals(user_id, exercise),
            directions=self._statistics.by_direction(user_id, exercise),
            most_missed=most_missed,
        )


class GetPracticeStatistics:
    """How the user does overall: totals, answers per day over the last
    `days` days in their time zone (today included, days without answers
    too), each exercise's figures, and the words and kanji missed most."""

    def __init__(
        self,
        statistics: ExerciseStatisticsRepository,
        entries: PracticeEntryRepository,
        kanji: PracticeKanjiRepository,
    ) -> None:
        self._statistics = statistics
        self._missed = _MissedItems(entries, kanji)

    def execute(
        self, user_id: UUID, now: datetime, days: int, tz: ZoneInfo
    ) -> PracticeStatistics:
        if not 1 <= days <= MAX_ACTIVITY_DAYS:
            raise ValueError(f"days must be between 1 and {MAX_ACTIVITY_DAYS}")
        return PracticeStatistics(
            totals=self._statistics.totals(user_id),
            activity=self._activity(user_id, now, days, tz),
            exercises=self._statistics.by_exercise(user_id),
            most_missed_entries=self._missed.entries(
                user_id,
                self._statistics.most_missed_entries(user_id, limit=MOST_MISSED_LIMIT),
            ),
            most_missed_kanji=self._missed.kanji(
                user_id,
                self._statistics.most_missed_kanji(user_id, limit=MOST_MISSED_LIMIT),
            ),
        )

    def _activity(
        self, user_id: UUID, now: datetime, days: int, tz: ZoneInfo
    ) -> list[DayActivity]:
        """Grouped here, not in SQL: SQLite and PostgreSQL would need
        different time zone functions."""
        first_day = now.astimezone(tz).date() - timedelta(days=days - 1)
        since = datetime.combine(first_day, time.min, tzinfo=tz)
        counts = {first_day + timedelta(days=i): [0, 0] for i in range(days)}
        for moment in self._statistics.answers_since(user_id, since):
            day = counts.get(moment.answered_at.astimezone(tz).date())
            if day is None:
                continue  # answered after `now`
            day[0] += 1
            day[1] += moment.is_correct
        return [
            DayActivity(day=day, answered=answered, correct=correct)
            for day, (answered, correct) in counts.items()
        ]
