import pytest
from factories import NOW, USER_ID, make_session

from shodoukan_practice.domain.entities import OptionAnswer
from shodoukan_practice.domain.exceptions import (
    EntityNotFoundError,
    InvalidAnswerError,
    QuestionAnsweredError,
)


def test_answer_grades_and_finishes_on_the_last_question() -> None:
    session = make_session(USER_ID, questions=2)

    right = session.answer(1, OptionAnswer(option=0), response_ms=1200)
    assert right.is_correct is True
    assert right.response_ms == 1200
    assert right.answered_at is not None
    assert session.finished_at is None
    assert session.updated_at > NOW

    wrong = session.answer(2, OptionAnswer(option=2))
    assert wrong.is_correct is False
    assert session.finished_at == wrong.answered_at
    assert session.score == 1


def test_a_question_is_answered_once() -> None:
    session = make_session(USER_ID)
    session.answer(1, OptionAnswer(option=1))
    with pytest.raises(QuestionAnsweredError):
        session.answer(1, OptionAnswer(option=0))


def test_unknown_question_or_option() -> None:
    session = make_session(USER_ID)
    with pytest.raises(EntityNotFoundError):
        session.answer(99, OptionAnswer(option=0))
    with pytest.raises(InvalidAnswerError):
        session.answer(1, OptionAnswer(option=3))  # 3 options: 0..2
    assert session.updated_at == NOW
