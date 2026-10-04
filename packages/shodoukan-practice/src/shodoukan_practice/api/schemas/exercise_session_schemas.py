"""Request and response models for exercise sessions.

An unanswered question shows only what the card's front shows: its prompt
and the options' texts. The item, the right option, the back and every
option's item appear once it's answered, so a client can't read the
solution ahead.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from ...domain.entities import (
    ExerciseAnswer,
    ExerciseQuestion,
    ExerciseSession,
    ItemKind,
    ShownField,
    StudyField,
)

MeaningLangCode = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern=r"^[a-z]{2,3}$")
]


class StartSessionRequest(BaseModel):
    meaning_lang: MeaningLangCode = Field(
        description=(
            "Language of the meanings, as the items store it: ISO 639-2 for "
            "entries (`eng`), ISO 639-1 for kanji (`en`)."
        )
    )


class AnswerRequest(BaseModel):
    answer: ExerciseAnswer = Field(
        description='The answer, by type. Choice cards: `{"type": "option", '
        '"option": <index>}`.'
    )
    response_ms: int | None = Field(
        default=None, ge=0, description="How long the user took, in milliseconds."
    )


class OptionResponse(BaseModel):
    text: str
    item_id: int | None = Field(
        description="The item the option comes from; null until answered."
    )


class QuestionResponse(BaseModel):
    id: int
    position: int
    prompt_fields: list[StudyField]
    answer_field: StudyField
    prompt: list[ShownField]
    options: list[OptionResponse]
    answered: bool
    # The solution: null until the question is answered.
    item_id: int | None
    correct_option: int | None
    back: list[ShownField] | None
    answer: ExerciseAnswer | None
    is_correct: bool | None
    answered_at: datetime | None
    response_ms: int | None

    @classmethod
    def of(cls, question: ExerciseQuestion) -> "QuestionResponse":
        assert question.id is not None
        answered = question.answered
        return cls(
            id=question.id,
            position=question.position,
            prompt_fields=list(question.prompt_fields),
            answer_field=question.answer_field,
            prompt=list(question.prompt),
            options=[
                OptionResponse(
                    text=option.text, item_id=option.item_id if answered else None
                )
                for option in question.options
            ],
            answered=answered,
            item_id=question.item_id if answered else None,
            correct_option=question.correct_option if answered else None,
            back=list(question.back) if answered else None,
            answer=question.answer,
            is_correct=question.is_correct,
            answered_at=question.answered_at,
            response_ms=question.response_ms,
        )


class SessionResponse(BaseModel):
    id: int
    exercise_id: int | None = Field(description="Null if the exercise was deleted.")
    exercise_name: str
    item_kind: ItemKind
    meaning_lang: str
    started_at: datetime
    finished_at: datetime | None
    score: int = Field(description="Questions answered right so far.")
    questions: list[QuestionResponse]

    @classmethod
    def of(cls, session: ExerciseSession) -> "SessionResponse":
        assert session.id is not None
        return cls(
            id=session.id,
            exercise_id=session.exercise_id,
            exercise_name=session.exercise_name,
            item_kind=session.item_kind,
            meaning_lang=session.meaning_lang,
            started_at=session.created_at,
            finished_at=session.finished_at,
            score=session.score,
            questions=[QuestionResponse.of(q) for q in session.questions],
        )


class AnswerResponse(BaseModel):
    question: QuestionResponse
    finished_at: datetime | None = Field(
        description="Set when this was the session's last question."
    )
    score: int
