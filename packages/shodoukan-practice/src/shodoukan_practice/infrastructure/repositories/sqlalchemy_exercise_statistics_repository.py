import json
from collections import defaultdict
from datetime import datetime
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import ColumnElement, String, case, cast, func, join, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from ...domain.entities import Exercise, ItemKind, StudyField
from ...domain.repositories import (
    AnswerMoment,
    AnswerTotals,
    DirectionTotals,
    ExerciseStatisticsRepository,
    ExerciseTotals,
    ItemTotals,
)
from ..db.orm import ExerciseORM, ExerciseQuestionORM, ExerciseSessionORM

_fields = TypeAdapter[list[StudyField]](list[StudyField])
_field = TypeAdapter[StudyField](StudyField)
_item_kind = TypeAdapter[ItemKind](ItemKind)

# 1 for a right answer, 0 otherwise; summed into counts.
_RIGHT = case((ExerciseQuestionORM.is_correct.is_(True), 1), else_=0)
_WRONG = case((ExerciseQuestionORM.is_correct.is_(False), 1), else_=0)

# Every query reads questions with their session (the owner, the exercise).
_QUESTIONS = join(
    ExerciseQuestionORM,
    ExerciseSessionORM,
    ExerciseSessionORM.id == ExerciseQuestionORM.session_id,
)


class SqlAlchemyExerciseStatisticsRepository(ExerciseStatisticsRepository):
    """Aggregates in SQL over the answered questions, joined to their session
    for the owner (and the exercise). Read-only.

    A direction's shown fields are a JSON list, which PostgreSQL can't group
    by: rows are grouped by its text and merged here into sets.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def totals(self, user_id: UUID, exercise: Exercise | None = None) -> AnswerTotals:
        query = (
            select(
                func.count(func.distinct(ExerciseQuestionORM.session_id)),
                func.count(ExerciseQuestionORM.id),
                func.coalesce(func.sum(_RIGHT), 0),
                func.avg(ExerciseQuestionORM.response_ms),
            )
            .select_from(_QUESTIONS)
            .where(*self._answered(user_id, exercise))
        )
        sessions, answered, correct, mean = self._session.execute(query).one()
        return AnswerTotals(
            sessions=sessions,
            answered=answered,
            correct=correct,
            mean_response_ms=float(mean) if mean is not None else None,
        )

    def by_direction(
        self, user_id: UUID, exercise: Exercise | None = None
    ) -> list[DirectionTotals]:
        prompt = cast(ExerciseQuestionORM.prompt_fields, String)
        query = (
            select(
                prompt,
                ExerciseQuestionORM.answer_field,
                func.count(ExerciseQuestionORM.id),
                func.sum(_RIGHT),
            )
            .select_from(_QUESTIONS)
            .where(*self._answered(user_id, exercise))
            .group_by(prompt, ExerciseQuestionORM.answer_field)
        )
        merged: defaultdict[tuple[frozenset[StudyField], StudyField], list[int]]
        merged = defaultdict(lambda: [0, 0])
        for prompt_text, answer_field, answered, correct in self._session.execute(
            query
        ):
            key = (
                frozenset(_fields.validate_python(json.loads(prompt_text))),
                _field.validate_python(answer_field),
            )
            merged[key][0] += answered
            merged[key][1] += correct
        rows = [
            DirectionTotals(
                prompt_fields=prompt_fields,
                answer_field=answer_field,
                answered=answered,
                correct=correct,
            )
            for (prompt_fields, answer_field), (answered, correct) in merged.items()
        ]
        return sorted(
            rows,
            key=lambda row: (
                -row.answered,
                sorted(row.prompt_fields),
                row.answer_field,
            ),
        )

    def most_missed_entries(
        self, user_id: UUID, exercise: Exercise | None = None, limit: int = 10
    ) -> list[ItemTotals]:
        return self._most_missed(ExerciseQuestionORM.entry_id, user_id, exercise, limit)

    def most_missed_kanji(
        self, user_id: UUID, exercise: Exercise | None = None, limit: int = 10
    ) -> list[ItemTotals]:
        return self._most_missed(ExerciseQuestionORM.kanji_id, user_id, exercise, limit)

    def by_exercise(self, user_id: UUID) -> list[ExerciseTotals]:
        last = func.max(ExerciseQuestionORM.answered_at)
        query = (
            select(
                ExerciseORM.id,
                ExerciseORM.name,
                ExerciseORM.item_kind,
                func.count(func.distinct(ExerciseQuestionORM.session_id)),
                func.count(ExerciseQuestionORM.id),
                func.sum(_RIGHT),
                last,
            )
            .select_from(_QUESTIONS)
            .join(ExerciseORM, ExerciseORM.id == ExerciseSessionORM.exercise_id)
            .where(*self._answered(user_id, None))
            .group_by(ExerciseORM.id, ExerciseORM.name, ExerciseORM.item_kind)
            .order_by(last.desc(), ExerciseORM.id)
        )
        return [
            ExerciseTotals(
                exercise_id=exercise_id,
                exercise_name=name,
                item_kind=_item_kind.validate_python(item_kind),
                sessions=sessions,
                answered=answered,
                correct=correct,
                last_answered_at=last_answered_at,
            )
            for (
                exercise_id,
                name,
                item_kind,
                sessions,
                answered,
                correct,
                last_answered_at,
            ) in self._session.execute(query)
        ]

    def answers_since(self, user_id: UUID, since: datetime) -> list[AnswerMoment]:
        query = (
            select(ExerciseQuestionORM.answered_at, ExerciseQuestionORM.is_correct)
            .select_from(_QUESTIONS)
            .where(
                *self._answered(user_id, None),
                ExerciseQuestionORM.answered_at >= since,
            )
            .order_by(ExerciseQuestionORM.answered_at, ExerciseQuestionORM.id)
        )
        moments: list[AnswerMoment] = []
        for answered_at, is_correct in self._session.execute(query):
            assert answered_at is not None  # only answered questions
            moments.append(
                AnswerMoment(answered_at=answered_at, is_correct=bool(is_correct))
            )
        return moments

    def _most_missed(
        self,
        item: InstrumentedAttribute[int | None],
        user_id: UUID,
        exercise: Exercise | None,
        limit: int,
    ) -> list[ItemTotals]:
        answered = func.count(ExerciseQuestionORM.id)
        wrong = func.sum(_WRONG)
        query = (
            select(item, answered, wrong)
            .select_from(_QUESTIONS)
            .where(*self._answered(user_id, exercise), item.is_not(None))
            .group_by(item)
            .having(wrong > 0)
            .order_by(wrong.desc(), answered, item)
            .limit(limit)
        )
        return [
            ItemTotals(item_id=item_id, answered=count, wrong=misses)
            for item_id, count, misses in self._session.execute(query)
        ]

    @staticmethod
    def _answered(
        user_id: UUID, exercise: Exercise | None
    ) -> list[ColumnElement[bool]]:
        filters: list[ColumnElement[bool]] = [
            ExerciseSessionORM.user_id == user_id,
            ExerciseQuestionORM.answered_at.is_not(None),
        ]
        if exercise is not None:
            filters.append(ExerciseSessionORM.exercise_id == exercise.id)
        return filters
