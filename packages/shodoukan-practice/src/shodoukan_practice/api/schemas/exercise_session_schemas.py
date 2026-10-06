"""Request and response models for exercise sessions.

The active question shows only what the card's front shows: its prompt, and
a choice card's option texts. Its item and back, a choice card's right option
and the options' items, and a handwriting card's reference strokes and grade,
appear once it's answered (in the history), so a client can't read the
solution ahead. Questions are a union keyed by `type`, so the client picks
how to play each one.
"""

from datetime import datetime
from typing import Annotated, Literal, assert_never

from pydantic import BaseModel, Field, StringConstraints

from ...domain.entities import (
    ChoiceQuestion,
    ExerciseAnswer,
    ExerciseQuestion,
    ExerciseSession,
    HandwritingGrade,
    HandwritingQuestion,
    ItemKind,
    Point,
    ReferenceKanji,
    ShownField,
    StudyField,
)
from ...domain.repositories import SessionSummary

# The largest value the `response_ms` column (a 32-bit INTEGER) can hold.
RESPONSE_MS_MAX = 2_147_483_647

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
    question_id: int = Field(description="The active question's id.")
    answer: ExerciseAnswer = Field(
        description='The answer, by type. Choice cards: `{"type": "option", '
        '"option": <index>}`. Handwriting cards: `{"type": "strokes", "strokes": '
        "[[[x, y], ...], ...]}`, the strokes in the order drawn, in KanjiVG's "
        "109-unit square (a margin of 6 around it is allowed). "
        '`{"type": "skip"}` skips either, which counts as a miss.'
    )
    response_ms: int | None = Field(
        default=None,
        ge=0,
        le=RESPONSE_MS_MAX,
        description="How long the user took, in milliseconds.",
    )


class OptionResponse(BaseModel):
    text: str
    item_id: int | None = Field(
        description="The item the option comes from; null until answered."
    )


class _QuestionResponse(BaseModel):
    id: int
    position: int
    prompt_fields: list[StudyField]
    answer_field: StudyField
    prompt: list[ShownField]
    answered: bool
    # The solution: null until the question is answered.
    item_id: int | None
    back: list[ShownField] | None
    answer: ExerciseAnswer | None
    is_correct: bool | None
    answered_at: datetime | None
    response_ms: int | None


class ChoiceQuestionResponse(_QuestionResponse):
    type: Literal["card.choice"] = "card.choice"
    options: list[OptionResponse]
    correct_option: int | None

    @classmethod
    def of(cls, question: ChoiceQuestion) -> "ChoiceQuestionResponse":
        assert question.id is not None
        answered = question.answered
        return cls(
            id=question.id,
            position=question.position,
            prompt_fields=list(question.prompt_fields),
            answer_field=question.answer_field,
            prompt=list(question.prompt),
            answered=answered,
            item_id=question.item_id if answered else None,
            back=list(question.back) if answered else None,
            answer=question.answer,
            is_correct=question.is_correct,
            answered_at=question.answered_at,
            response_ms=question.response_ms,
            options=[
                OptionResponse(
                    text=option.text, item_id=option.item_id if answered else None
                )
                for option in question.options
            ],
            correct_option=question.correct_option if answered else None,
        )


class ReferenceStrokeResponse(BaseModel):
    path: str = Field(description="SVG path of the stroke's centre line (KanjiVG).")
    label: Point | None = Field(description="Where the stroke's number goes.")


class ReferenceKanjiResponse(BaseModel):
    literal: str
    strokes: list[ReferenceStrokeResponse]

    @classmethod
    def of(cls, reference: ReferenceKanji) -> "ReferenceKanjiResponse":
        return cls(
            literal=reference.literal,
            strokes=[
                ReferenceStrokeResponse(path=s.path, label=s.label)
                for s in reference.strokes
            ],
        )


class HandwritingQuestionResponse(_QuestionResponse):
    type: Literal["card.handwriting"] = "card.handwriting"
    references: list[ReferenceKanjiResponse] | None = Field(
        description="The kanji it accepts, with their strokes; null until answered."
    )
    grade: HandwritingGrade | None = Field(
        description="How the drawing compares to the closest accepted kanji; null "
        "until answered, and when skipped."
    )

    @classmethod
    def of(cls, question: HandwritingQuestion) -> "HandwritingQuestionResponse":
        assert question.id is not None
        answered = question.answered
        return cls(
            id=question.id,
            position=question.position,
            prompt_fields=list(question.prompt_fields),
            answer_field=question.answer_field,
            prompt=list(question.prompt),
            answered=answered,
            item_id=question.item_id if answered else None,
            back=list(question.back) if answered else None,
            answer=question.answer,
            is_correct=question.is_correct,
            answered_at=question.answered_at,
            response_ms=question.response_ms,
            references=(
                [ReferenceKanjiResponse.of(r) for r in question.references]
                if answered
                else None
            ),
            grade=question.grade,
        )


QuestionResponse = Annotated[
    ChoiceQuestionResponse | HandwritingQuestionResponse,
    Field(discriminator="type"),
]


def question_response(
    question: ExerciseQuestion,
) -> ChoiceQuestionResponse | HandwritingQuestionResponse:
    if isinstance(question, ChoiceQuestion):
        return ChoiceQuestionResponse.of(question)
    if isinstance(question, HandwritingQuestion):
        return HandwritingQuestionResponse.of(question)
    assert_never(question)


class SessionResponse(BaseModel):
    id: int
    exercise_id: int | None = Field(description="Null if the exercise was deleted.")
    exercise_name: str
    item_kind: ItemKind
    meaning_lang: str
    started_at: datetime
    last_activity_at: datetime
    finished_at: datetime | None = Field(
        description="When it was closed, or its last activity if it's been idle "
        "too long; null while it's open."
    )
    answered: int = Field(description="Questions answered.")
    score: int = Field(description="Questions answered right.")
    current: QuestionResponse | None = Field(
        description="The active question, without its solution."
    )
    history: list[QuestionResponse] = Field(
        description="The answered questions, in order, with their solutions."
    )

    @classmethod
    def of(cls, session: ExerciseSession, now: datetime) -> "SessionResponse":
        assert session.id is not None
        finished_at = session.ended_at(now)
        current = session.current if finished_at is None else None
        return cls(
            id=session.id,
            exercise_id=session.exercise_id,
            exercise_name=session.exercise_name,
            item_kind=session.item_kind,
            meaning_lang=session.meaning_lang,
            started_at=session.created_at,
            last_activity_at=session.updated_at,
            finished_at=finished_at,
            answered=session.answered,
            score=session.score,
            current=question_response(current) if current else None,
            history=[question_response(q) for q in session.history],
        )


class AnswerResponse(BaseModel):
    answered: QuestionResponse = Field(description="The graded question.")
    next: QuestionResponse | None = Field(
        description="The new active question; null if no other can be made (or "
        "the exercise was deleted, which finishes the session)."
    )
    answered_count: int
    score: int
    finished_at: datetime | None


class SessionSummaryResponse(BaseModel):
    """A session in the history: its figures, without its questions."""

    id: int
    exercise_id: int | None = Field(description="Null if the exercise was deleted.")
    exercise_name: str
    item_kind: ItemKind
    started_at: datetime
    last_activity_at: datetime
    finished_at: datetime | None = Field(
        description="When it was closed, or its last activity if it's been idle "
        "too long; null while it's open."
    )
    answered: int
    score: int

    @classmethod
    def of(cls, summary: SessionSummary, now: datetime) -> "SessionSummaryResponse":
        return cls(
            id=summary.id,
            exercise_id=summary.exercise_id,
            exercise_name=summary.exercise_name,
            item_kind=summary.item_kind,
            started_at=summary.started_at,
            last_activity_at=summary.last_activity_at,
            finished_at=summary.ended_at(now),
            answered=summary.answered,
            score=summary.score,
        )


class SessionSummaryPageResponse(BaseModel):
    items: list[SessionSummaryResponse]
    total: int  # sessions matching the request, across every page
    limit: int
    offset: int
