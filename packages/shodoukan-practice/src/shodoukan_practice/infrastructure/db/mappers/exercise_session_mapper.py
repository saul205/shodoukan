"""ExerciseSession <-> exercise_sessions and exercise_questions.

The active question and the history share `exercise_questions`: the active
one is the row with no answer. The question's item goes to `entry_id` or
`kanji_id` by the session's item kind. Prompt, back and answer are stored as
JSON-compatible lists and dicts, validated back into the domain's value
objects. `type` picks the question class through the `ExerciseQuestion`
union, as `settings` does for exercises, and `details` holds the fields only
that class has (everything but `QuestionBase`'s), validated by it on the way
back.
"""

from typing import Any

from pydantic import TypeAdapter

from ....domain.entities import (
    ExerciseAnswer,
    ExerciseQuestion,
    ExerciseSession,
    ItemKind,
    QuestionBase,
    ShownField,
    StudyField,
)
from ..orm import ExerciseQuestionORM, ExerciseSessionORM

_shown = TypeAdapter[tuple[ShownField, ...]](tuple[ShownField, ...])
_answer = TypeAdapter[ExerciseAnswer | None](ExerciseAnswer | None)
_fields = TypeAdapter[tuple[StudyField, ...]](tuple[StudyField, ...])
_field = TypeAdapter[StudyField](StudyField)
_item_kind = TypeAdapter[ItemKind](ItemKind)

_question = TypeAdapter[ExerciseQuestion](ExerciseQuestion)
# Stored in their own columns; every other field of a question is `details`.
_COLUMNS = {*QuestionBase.model_fields, "type"}


def exercise_session_to_domain(row: ExerciseSessionORM) -> ExerciseSession:
    item_kind = _item_kind.validate_python(row.item_kind)
    questions = [_question_to_domain(q, item_kind) for q in row.questions]
    pending = [q for q in questions if not q.answered]
    return ExerciseSession(
        id=row.id,
        user_id=row.user_id,
        exercise_id=row.exercise_id,
        exercise_name=row.exercise_name,
        item_kind=item_kind,
        meaning_lang=row.meaning_lang,
        current=pending[-1] if pending else None,
        history=[q for q in questions if q.answered],
        finished_at=row.finished_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def exercise_session_to_db(entity: ExerciseSession) -> ExerciseSessionORM:
    return ExerciseSessionORM(
        id=entity.id,
        user_id=entity.user_id,
        exercise_id=entity.exercise_id,
        exercise_name=entity.exercise_name,
        item_kind=entity.item_kind,
        meaning_lang=entity.meaning_lang,
        questions=[
            _question_to_db(question, entity)
            for question in [
                *entity.history,
                *([entity.current] if entity.current else []),
            ]
        ],
        finished_at=entity.finished_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _question_to_domain(
    row: ExerciseQuestionORM, item_kind: ItemKind
) -> ExerciseQuestion:
    common: dict[str, Any] = {
        "type": row.type,
        "id": row.id,
        "position": row.position,
        "item_id": row.entry_id if item_kind == "entries" else row.kanji_id,
        "prompt_fields": _fields.validate_python(row.prompt_fields),
        "answer_field": _field.validate_python(row.answer_field),
        "prompt": _shown.validate_python(row.prompt),
        "back": _shown.validate_python(row.back),
        "answer": _answer.validate_python(row.answer),
        "is_correct": row.is_correct,
        "answered_at": row.answered_at,
        "response_ms": row.response_ms,
    }
    return _question.validate_python({**row.details, **common})


def _question_to_db(
    question: ExerciseQuestion, session: ExerciseSession
) -> ExerciseQuestionORM:
    by_entry = session.item_kind == "entries"
    return ExerciseQuestionORM(
        id=question.id,
        session_id=session.id,
        position=question.position,
        entry_id=question.item_id if by_entry else None,
        kanji_id=None if by_entry else question.item_id,
        prompt_fields=list(question.prompt_fields),
        answer_field=question.answer_field,
        prompt=_shown.dump_python(question.prompt, mode="json"),
        type=question.type,
        back=_shown.dump_python(question.back, mode="json"),
        details=question.model_dump(mode="json", exclude=_COLUMNS),
        answer=_answer.dump_python(question.answer, mode="json"),
        is_correct=question.is_correct,
        answered_at=question.answered_at,
        response_ms=question.response_ms,
    )
