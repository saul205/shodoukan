"""Response models for exercise statistics.

`accuracy` is right answers over answers (from 0 to 1), null when there are none, so
clients needn't divide.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field

from ...application.queries import (
    DayActivity,
    ExerciseStatistics,
    MissedItem,
    PracticeStatistics,
)
from ...domain.entities import ItemKind, StudyField
from ...domain.repositories import AnswerTotals, DirectionTotals, ExerciseTotals


def _accuracy(correct: int, answered: int) -> float | None:
    return correct / answered if answered else None


class TotalsResponse(BaseModel):
    sessions: int = Field(description="Sessions with at least one answer.")
    answered: int
    correct: int
    accuracy: float | None
    mean_response_ms: float | None

    @classmethod
    def of(cls, totals: AnswerTotals) -> "TotalsResponse":
        return cls(
            sessions=totals.sessions,
            answered=totals.answered,
            correct=totals.correct,
            accuracy=_accuracy(totals.correct, totals.answered),
            mean_response_ms=totals.mean_response_ms,
        )


class DirectionStatisticsResponse(BaseModel):
    prompt_fields: list[StudyField] = Field(
        description="The fields shown, in a fixed order (a direction is the "
        "same whatever their order)."
    )
    answer_field: StudyField
    answered: int
    correct: int
    accuracy: float | None

    @classmethod
    def of(cls, direction: DirectionTotals) -> "DirectionStatisticsResponse":
        return cls(
            prompt_fields=sorted(direction.prompt_fields),
            answer_field=direction.answer_field,
            answered=direction.answered,
            correct=direction.correct,
            accuracy=_accuracy(direction.correct, direction.answered),
        )


class MissedItemResponse(BaseModel):
    item_id: int = Field(description="The entry's or the kanji's library id.")
    label: str = Field(description="A word's usual form, or the kanji.")
    reading: str | None = Field(description="A word's reading, if `label` isn't it.")
    answered: int
    wrong: int

    @classmethod
    def of(cls, item: MissedItem) -> "MissedItemResponse":
        return cls(
            item_id=item.item_id,
            label=item.label,
            reading=item.reading,
            answered=item.answered,
            wrong=item.wrong,
        )


class ExerciseStatisticsResponse(BaseModel):
    exercise_id: int
    item_kind: ItemKind
    totals: TotalsResponse
    directions: list[DirectionStatisticsResponse] = Field(
        description="Most answered first."
    )
    most_missed: list[MissedItemResponse] = Field(
        description="Items of the exercise's kind, most misses first."
    )

    @classmethod
    def of(cls, statistics: ExerciseStatistics) -> "ExerciseStatisticsResponse":
        assert statistics.exercise.id is not None
        return cls(
            exercise_id=statistics.exercise.id,
            item_kind=statistics.exercise.item_kind,
            totals=TotalsResponse.of(statistics.totals),
            directions=[
                DirectionStatisticsResponse.of(d) for d in statistics.directions
            ],
            most_missed=[MissedItemResponse.of(i) for i in statistics.most_missed],
        )


class DayActivityResponse(BaseModel):
    day: date = Field(description="In the requested time zone.")
    answered: int
    correct: int

    @classmethod
    def of(cls, day: DayActivity) -> "DayActivityResponse":
        return cls(day=day.day, answered=day.answered, correct=day.correct)


class ExerciseSummaryResponse(BaseModel):
    exercise_id: int
    exercise_name: str = Field(description="Its current name.")
    item_kind: ItemKind
    sessions: int
    answered: int
    correct: int
    accuracy: float | None
    last_answered_at: datetime

    @classmethod
    def of(cls, totals: ExerciseTotals) -> "ExerciseSummaryResponse":
        return cls(
            exercise_id=totals.exercise_id,
            exercise_name=totals.exercise_name,
            item_kind=totals.item_kind,
            sessions=totals.sessions,
            answered=totals.answered,
            correct=totals.correct,
            accuracy=_accuracy(totals.correct, totals.answered),
            last_answered_at=totals.last_answered_at,
        )


class PracticeStatisticsResponse(BaseModel):
    totals: TotalsResponse
    activity: list[DayActivityResponse] = Field(
        description="Every day of the window, oldest first; today is the last."
    )
    exercises: list[ExerciseSummaryResponse] = Field(
        description="Exercises with answers, most recently answered first; "
        "deleted ones left out."
    )
    most_missed_entries: list[MissedItemResponse]
    most_missed_kanji: list[MissedItemResponse]

    @classmethod
    def of(cls, statistics: PracticeStatistics) -> "PracticeStatisticsResponse":
        return cls(
            totals=TotalsResponse.of(statistics.totals),
            activity=[DayActivityResponse.of(d) for d in statistics.activity],
            exercises=[ExerciseSummaryResponse.of(e) for e in statistics.exercises],
            most_missed_entries=[
                MissedItemResponse.of(i) for i in statistics.most_missed_entries
            ],
            most_missed_kanji=[
                MissedItemResponse.of(i) for i in statistics.most_missed_kanji
            ],
        )
