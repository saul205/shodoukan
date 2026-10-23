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

Questions and answers are unions discriminated by `type`, like exercise
settings. A `ChoiceQuestion` is answered with an `OptionAnswer`; a
`HandwritingQuestion` with a `StrokesAnswer` (the drawn kanji), graded by
`handwriting_grading_service` against the KanjiVG strokes of the kanji it
accepts; a `WordHandwritingQuestion` with a `CellsAnswer` (a word written a
character per cell), each cell graded the same way (`word_grading_service`).
A `SkipAnswer` fits them all and counts as a miss.
"""

from datetime import datetime, timedelta
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


# The drawing space: KanjiVG's square, plus the margin the canvas shows
# around it (strokes may run slightly outside the square).
CANVAS_SIZE = 109
CANVAS_MARGIN = 6
MAX_STROKES = 40
MAX_STROKE_POINTS = 300
# The longest word written by hand, in characters (cells).
MAX_CELLS = 12

Point = tuple[float, float]
DrawnStroke = Annotated[
    tuple[Point, ...], Field(min_length=1, max_length=MAX_STROKE_POINTS)
]


class StrokesAnswer(BaseModel):
    """The kanji as drawn: its strokes in the order drawn, each a list of
    points in the canvas space (`CANVAS_SIZE`, `CANVAS_MARGIN`)."""

    model_config = ConfigDict(frozen=True)

    type: Literal["strokes"] = "strokes"
    strokes: tuple[DrawnStroke, ...] = Field(min_length=1, max_length=MAX_STROKES)

    @field_validator("strokes")
    @classmethod
    def _check_bounds(
        cls, strokes: tuple[tuple[Point, ...], ...]
    ) -> tuple[tuple[Point, ...], ...]:
        _check_on_canvas(strokes)
        return strokes


DrawnCell = Annotated[tuple[DrawnStroke, ...], Field(max_length=MAX_STROKES)]


class CellsAnswer(BaseModel):
    """A word as written: one drawing per character, in order, each in its
    own cell with the same space as `StrokesAnswer`. A cell may be left empty
    (that character is missing), but not all of them."""

    model_config = ConfigDict(frozen=True)

    type: Literal["cells"] = "cells"
    cells: tuple[DrawnCell, ...] = Field(min_length=1, max_length=MAX_CELLS)

    @field_validator("cells")
    @classmethod
    def _check_cells(
        cls, cells: tuple[tuple[tuple[Point, ...], ...], ...]
    ) -> tuple[tuple[tuple[Point, ...], ...], ...]:
        if not any(cells):
            raise ValueError("a word needs at least one character drawn")
        for cell in cells:
            _check_on_canvas(cell)
        return cells


def _check_on_canvas(strokes: tuple[tuple[Point, ...], ...]) -> None:
    low, high = -CANVAS_MARGIN, CANVAS_SIZE + CANVAS_MARGIN
    for stroke in strokes:
        for x, y in stroke:
            if not (low <= x <= high and low <= y <= high):
                raise ValueError(f"point ({x}, {y}) is outside the canvas")


class ReferenceStroke(BaseModel):
    """One stroke of a reference kanji (KanjiVG): its path, to draw it, the
    place of its number, and its centre line as points, to grade against."""

    model_config = ConfigDict(frozen=True)

    path: str
    label: Point | None
    points: tuple[Point, ...] = Field(min_length=1)


class ReferenceKanji(BaseModel):
    """A kanji a handwriting question accepts, with its strokes in order."""

    model_config = ConfigDict(frozen=True)

    literal: str
    strokes: tuple[ReferenceStroke, ...] = Field(min_length=1)


class ReferenceWord(BaseModel):
    """A word a handwriting question accepts, a reference per character."""

    model_config = ConfigDict(frozen=True)

    text: str
    characters: tuple[ReferenceKanji, ...] = Field(min_length=1, max_length=MAX_CELLS)

    @model_validator(mode="after")
    def _check_text(self) -> Self:
        if "".join(c.literal for c in self.characters) != self.text:
            raise ValueError("a word's references must spell it, one per character")
        return self


# How a drawn stroke compares to the reference: right; right place and
# shape but drawn backwards; right but out of order; too long or too short
# for the rest of the kanji; too far from its reference stroke; one the
# reference doesn't have; one not drawn.
StrokeStatus = Literal[
    "ok",
    "reversed",
    "out_of_order",
    "too_long",
    "too_short",
    "imprecise",
    "extra",
    "missing",
]
# Right; right enough to count, but to practise again; wrong.
Verdict = Literal["correct", "close", "wrong"]


class StrokeFeedback(BaseModel):
    """One stroke's grade. `drawn` and `reference` are stroke indexes: an
    extra stroke has no reference, a missing one wasn't drawn."""

    model_config = ConfigDict(frozen=True)

    drawn: int | None = Field(ge=0)
    reference: int | None = Field(ge=0)
    status: StrokeStatus


class HandwritingGrade(BaseModel):
    """How a drawing compares to the closest accepted kanji (`matched`).
    `looks_like` names the character it was taken for when it's wrong for
    being another one (ろ for る, や for ゃ)."""

    model_config = ConfigDict(frozen=True)

    score: int = Field(ge=0, le=100)
    verdict: Verdict
    matched: str
    strokes: tuple[StrokeFeedback, ...]
    looks_like: str | None = None


class WordGrade(BaseModel):
    """How a written word compares to the closest accepted one (`matched`):
    each cell's grade against its character. The verdict is the worst
    cell's, and the score their average."""

    model_config = ConfigDict(frozen=True)

    score: int = Field(ge=0, le=100)
    verdict: Verdict
    matched: str
    cells: tuple[HandwritingGrade, ...] = Field(min_length=1)


class SkipAnswer(BaseModel):
    """The user skipped the question: it counts as a miss (it comes back as a
    review, and the solution is shown), like answering "I don't know"."""

    model_config = ConfigDict(frozen=True)

    type: Literal["skip"] = "skip"


# Answers of every exercise type, by `type`.
ExerciseAnswer = Annotated[
    OptionAnswer | StrokesAnswer | CellsAnswer | SkipAnswer,
    Field(discriminator="type"),
]


class QuestionBase(BaseModel):
    """What every question has: the card it shows and how it was answered."""

    id: int | None
    position: int
    # The item asked about; None once it's removed from the library.
    item_id: int | None
    prompt_fields: tuple[StudyField, ...]
    answer_field: StudyField
    prompt: tuple[ShownField, ...]
    back: tuple[ShownField, ...]
    answer: ExerciseAnswer | None = None
    is_correct: bool | None = None
    answered_at: datetime | None = None
    # How long the user took, as measured by the client.
    response_ms: int | None = None

    @property
    def answered(self) -> bool:
        return self.answer is not None

    @property
    def needs_review(self) -> bool:
        """Whether its item should come back as a review: it was missed."""
        return self.is_correct is False


class ChoiceQuestion(QuestionBase):
    """Pick the right answer among `options`."""

    type: Literal["card.choice"] = "card.choice"
    options: tuple[ChoiceOption, ...]
    correct_option: int


class HandwritingQuestion(QuestionBase):
    """Draw the kanji. Any of `references` is right: the kanji asked about, and
    any other of the pool that fits the prompt too (two kanji read はし)."""

    type: Literal["card.handwriting"] = "card.handwriting"
    references: tuple[ReferenceKanji, ...] = Field(min_length=1)
    grade: HandwritingGrade | None = None

    @property
    def needs_review(self) -> bool:
        """Missed, or drawn well enough to count but worth practising again."""
        close = self.grade is not None and self.grade.verdict == "close"
        return self.is_correct is False or close


class WordHandwritingQuestion(QuestionBase):
    """Write the word (its spelling or its reading, by `answer_field`), a
    character per cell. Any of `words` is right, as with kanji: the word asked
    about, and any other of the pool that fits the prompt and has as many
    characters (the cells are shown, so their number is a given)."""

    type: Literal["card.handwriting_word"] = "card.handwriting_word"
    words: tuple[ReferenceWord, ...] = Field(min_length=1)
    grade: WordGrade | None = None

    @model_validator(mode="after")
    def _check_lengths(self) -> Self:
        if len({len(word.characters) for word in self.words}) != 1:
            raise ValueError("the words a question accepts have as many characters")
        return self

    @property
    def cell_count(self) -> int:
        """The cells to write in: the characters of the words it accepts."""
        return len(self.words[0].characters)

    @property
    def needs_review(self) -> bool:
        """Missed, or written well enough to count but worth practising again."""
        close = self.grade is not None and self.grade.verdict == "close"
        return self.is_correct is False or close


# Questions of every exercise type, by `type`.
ExerciseQuestion = Annotated[
    ChoiceQuestion | HandwritingQuestion | WordHandwritingQuestion,
    Field(discriminator="type"),
]


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
        self,
        question_id: int,
        answer: ExerciseAnswer,
        response_ms: int | None = None,
        grade: HandwritingGrade | WordGrade | None = None,
    ) -> ExerciseQuestion:
        """Grade the active question and move it to the history.

        `question_id` must be the active question's, so an answer meant for
        another one (a double click, a stale tab) is rejected with
        `QuestionNotActiveError`. Raises `SessionFinishedError` if the session
        is closed or idle (nothing changes) and `InvalidAnswerError` for an
        answer that doesn't fit the question (another type's, or an option it
        doesn't have). A `SkipAnswer` is graded as a miss.

        A drawing is graded by `handwriting_grading_service` (a word, by
        `word_grading_service`), which the caller runs on the question's
        references and passes as `grade`; it counts as right unless the
        grade's verdict is "wrong".
        """
        self._require_open()
        question = self.current
        if question is None or question.id != question_id:
            raise QuestionNotActiveError(f"question {question_id} isn't the active one")
        if grade is not None and not isinstance(answer, StrokesAnswer | CellsAnswer):
            raise ValueError("only a drawing is graded with a handwriting grade")
        if isinstance(answer, SkipAnswer):
            question.is_correct = False  # skipped: a miss
        elif isinstance(question, ChoiceQuestion):
            question.is_correct = _grade_option(question, answer)
        elif isinstance(question, HandwritingQuestion):
            question.is_correct = _record_grade(question, answer, grade)
        else:
            question.is_correct = _record_word_grade(question, answer, grade)
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


def _grade_option(question: ChoiceQuestion, answer: ExerciseAnswer) -> bool:
    if not isinstance(answer, OptionAnswer):
        raise InvalidAnswerError(f"question {question.id} is answered with an option")
    if answer.option >= len(question.options):
        raise InvalidAnswerError(
            f"question {question.id} has no option {answer.option}"
        )
    return answer.option == question.correct_option


def _record_grade(
    question: HandwritingQuestion,
    answer: ExerciseAnswer,
    grade: HandwritingGrade | WordGrade | None,
) -> bool:
    if not isinstance(answer, StrokesAnswer):
        raise InvalidAnswerError(f"question {question.id} is answered with a drawing")
    if not isinstance(grade, HandwritingGrade):
        raise ValueError("a drawing needs its grade")
    if grade.matched not in {r.literal for r in question.references}:
        raise ValueError(f"{grade.matched} isn't a kanji the question accepts")
    question.grade = grade
    return grade.verdict != "wrong"


def _record_word_grade(
    question: WordHandwritingQuestion,
    answer: ExerciseAnswer,
    grade: HandwritingGrade | WordGrade | None,
) -> bool:
    if not isinstance(answer, CellsAnswer):
        raise InvalidAnswerError(
            f"question {question.id} is answered with a drawing per character"
        )
    if len(answer.cells) != question.cell_count:
        raise InvalidAnswerError(
            f"question {question.id} is written in {question.cell_count} cells"
        )
    if not isinstance(grade, WordGrade):
        raise ValueError("a written word needs its grade")
    if grade.matched not in {w.text for w in question.words}:
        raise ValueError(f"{grade.matched} isn't a word the question accepts")
    question.grade = grade
    return grade.verdict != "wrong"
