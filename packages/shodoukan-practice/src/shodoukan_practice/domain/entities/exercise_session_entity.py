"""One run of an exercise: its questions and the answers given.

A question keeps a snapshot of what was shown (prompt, options, back of the
card), so a session reads the same later even if its items are edited or
removed from the library. Sessions are also the statistics: accuracy and
history are queries over them. See docs/practice/technical/exercises.md.

`answer` is a union discriminated by `type`, like exercise settings; only
`OptionAnswer` (choice cards) exists for now.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..clock import utc_now
from ..exceptions import EntityNotFoundError, InvalidAnswerError, QuestionAnsweredError
from .exercise_entity import ItemKind, StudyField
from .timestamped_entity import TimestampedEntity


class ShownField(BaseModel):
    """A field of the item as shown on the card, with all its values."""

    model_config = ConfigDict(frozen=True)

    field: StudyField
    values: tuple[str, ...]


class ChoiceOption(BaseModel):
    """An option of a choice card; `item_id` is the item it was taken from."""

    model_config = ConfigDict(frozen=True)

    text: str
    item_id: int | None


class OptionAnswer(BaseModel):
    """The option picked, by its index in `options`."""

    model_config = ConfigDict(frozen=True)

    type: Literal["option"] = "option"
    option: int = Field(ge=0)


# Answers of every exercise type. With a second type this becomes
# `Annotated[OptionAnswer | TextAnswer, Field(discriminator="type")]`.
ExerciseAnswer = OptionAnswer


class ExerciseQuestion(BaseModel):
    id: int | None
    position: int
    # The item asked about; None once it's removed from the library.
    item_id: int | None
    prompt_fields: tuple[StudyField, ...]
    answer_field: StudyField
    prompt: tuple[ShownField, ...]
    options: tuple[ChoiceOption, ...]
    correct_option: int
    back: tuple[ShownField, ...]
    answer: ExerciseAnswer | None = None
    is_correct: bool | None = None
    answered_at: datetime | None = None
    # How long the user took, as measured by the client.
    response_ms: int | None = None

    @property
    def answered(self) -> bool:
        return self.answer is not None


class ExerciseSession(TimestampedEntity):
    """`created_at` is when it started; `finished_at` when the last question
    was answered."""

    id: int | None
    user_id: UUID
    # None once the exercise is deleted; the session stays in the history.
    exercise_id: int | None
    exercise_name: str
    item_kind: ItemKind
    meaning_lang: str
    questions: list[ExerciseQuestion] = Field(min_length=1)
    finished_at: datetime | None = None

    def answer(
        self, question_id: int, answer: ExerciseAnswer, response_ms: int | None = None
    ) -> ExerciseQuestion:
        """Grade `answer` to a question, once. Finishes the session when it's
        the last one.

        Raises `EntityNotFoundError` for an unknown question,
        `QuestionAnsweredError` if it was answered already and
        `InvalidAnswerError` for an option it doesn't have.
        """
        question = self._question(question_id)
        if question.answered:
            raise QuestionAnsweredError(f"question {question_id} is already answered")
        if answer.option >= len(question.options):
            raise InvalidAnswerError(
                f"question {question_id} has no option {answer.option}"
            )
        now = utc_now()
        question.answer = answer
        question.is_correct = answer.option == question.correct_option
        question.answered_at = now
        question.response_ms = response_ms
        if all(q.answered for q in self.questions):
            self.finished_at = now
        self.touch()
        return question

    @property
    def score(self) -> int:
        """Questions answered right."""
        return sum(1 for q in self.questions if q.is_correct)

    def _question(self, question_id: int) -> ExerciseQuestion:
        for question in self.questions:
            if question.id == question_id:
                return question
        raise EntityNotFoundError(f"question {question_id} not found")
