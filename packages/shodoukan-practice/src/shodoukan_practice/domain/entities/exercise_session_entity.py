"""One run of an exercise: an open-ended study session.

A session has one active question (`current`) and the questions already
answered (`history`). Answering the active one moves it to the history; the
next one is asked by the application, which builds it from the history (so it
doesn't repeat) and the exercise. The session lasts until it's finished, or
until it's idle for `IDLE_TIMEOUT`.

A question keeps a snapshot of what was shown (prompt, options, back of the
card), so a session reads the same later even if its items are edited or
removed from the library. The history is also the statistics. See
docs/practice/technical/exercises.md.

`answer` is a union discriminated by `type`, like exercise settings: an
`OptionAnswer` (choice cards) or a `SkipAnswer`, which counts as a miss.
"""

from datetime import datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..clock import utc_now
from ..exceptions import (
    InvalidAnswerError,
    QuestionNotActiveError,
    SessionFinishedError,
)
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


class SkipAnswer(BaseModel):
    """The user skipped the question: it counts as a miss (it comes back as a
    review, and the solution is shown), like answering "I don't know"."""

    model_config = ConfigDict(frozen=True)

    type: Literal["skip"] = "skip"


# Answers of every exercise type, by `type`.
ExerciseAnswer = Annotated[OptionAnswer | SkipAnswer, Field(discriminator="type")]


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


# A session nobody touched for this long counts as finished at its last activity.
IDLE_TIMEOUT = timedelta(minutes=30)

# How history lists filter sessions: still open (closed nor idle), or ended.
SessionStatus = Literal["open", "finished"]


def session_end(
    finished_at: datetime | None, last_activity: datetime, now: datetime
) -> datetime | None:
    """When a session ended: when it was closed, or its last activity if it's
    been idle longer than `IDLE_TIMEOUT`; None while it's open. The one rule
    for sessions and their summaries alike."""
    if finished_at is not None:
        return finished_at
    if now - last_activity > IDLE_TIMEOUT:
        return last_activity
    return None


class ExerciseSession(TimestampedEntity):
    """`created_at` is when it started, `updated_at` its last activity and
    `finished_at` when it was closed."""

    id: int | None
    user_id: UUID
    # None once the exercise is deleted; the session stays in the history.
    exercise_id: int | None
    exercise_name: str
    item_kind: ItemKind
    meaning_lang: str
    # The active question, not answered yet.
    current: ExerciseQuestion | None = None
    # The answered questions, in the order they were asked.
    history: list[ExerciseQuestion] = Field(default_factory=list)
    finished_at: datetime | None = None

    @property
    def is_finished(self) -> bool:
        return self.finished_at is not None

    def ended_at(self, now: datetime) -> datetime | None:
        """When it ended: closed, or idle since its last activity; None if open."""
        return session_end(self.finished_at, self.updated_at, now)

    def ask(self, question: ExerciseQuestion) -> None:
        """Make `question` the active one. Raises `SessionFinishedError` if the
        session is closed or idle, `QuestionNotActiveError` if one is already
        active."""
        self._require_open()
        if self.current is not None:
            raise QuestionNotActiveError("the session already has an active question")
        self.current = question.model_copy(
            update={"id": None, "position": len(self.history)}
        )
        self.touch()

    def answer(
        self, question_id: int, answer: ExerciseAnswer, response_ms: int | None = None
    ) -> ExerciseQuestion:
        """Grade the active question and move it to the history.

        `question_id` must be the active question's, so an answer meant for
        another one (a double click, a stale tab) is rejected with
        `QuestionNotActiveError`. Raises `SessionFinishedError` if the session
        is closed or idle (nothing changes) and `InvalidAnswerError` for an
        option it doesn't have. A `SkipAnswer` is graded as a miss.
        """
        self._require_open()
        question = self.current
        if question is None or question.id != question_id:
            raise QuestionNotActiveError(f"question {question_id} isn't the active one")
        if isinstance(answer, OptionAnswer):
            if answer.option >= len(question.options):
                raise InvalidAnswerError(
                    f"question {question_id} has no option {answer.option}"
                )
            question.is_correct = answer.option == question.correct_option
        else:
            question.is_correct = False  # skipped: a miss
        question.answer = answer
        question.answered_at = utc_now()
        question.response_ms = response_ms
        self.history.append(question)
        self.current = None
        self.touch()
        return question

    def finish(self) -> None:
        """The user closes the session now; the active question, never
        answered, is dropped. Closing a closed session changes nothing."""
        if self.is_finished:
            return
        self.current = None
        self.finished_at = utc_now()
        self.touch()

    def close_at_last_activity(self) -> None:
        """Close a session the user left: it ends at its last activity, and
        closing it isn't activity, so `updated_at` stays (unlike `touch()`
        elsewhere). The active question is dropped. A closed session stays as
        it is."""
        if self.is_finished:
            return
        self.current = None
        self.finished_at = self.updated_at

    def close_if_idle(self, now: datetime) -> bool:
        """Close it at its last activity if it's been idle too long."""
        if self.is_finished or self.ended_at(now) is None:
            return False
        self.close_at_last_activity()
        return True

    @property
    def answered(self) -> int:
        return len(self.history)

    @property
    def score(self) -> int:
        """Questions answered right."""
        return sum(1 for q in self.history if q.is_correct)

    def _require_open(self) -> None:
        """Closed or idle: an idle session counts as finished without being
        written (see `ended_at`), so nothing is asked or answered in it."""
        if self.ended_at(utc_now()) is not None:
            raise SessionFinishedError(f"exercise session {self.id} is finished")
