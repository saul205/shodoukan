from datetime import timedelta

import pytest
from factories import NOW, USER_ID, make_question, make_session

from shodoukan_practice.domain.entities import ExerciseSession, OptionAnswer
from shodoukan_practice.domain.entities.exercise_session_entity import IDLE_TIMEOUT
from shodoukan_practice.domain.exceptions import (
    InvalidAnswerError,
    QuestionNotActiveError,
    SessionFinishedError,
)


def _store_current(session: ExerciseSession, question_id: int) -> None:
    """What the repository does: the active question gets an id."""
    assert session.current is not None
    session.current.id = question_id


def test_answer_moves_the_active_question_to_the_history() -> None:
    session = make_session(USER_ID)

    graded = session.answer(1, OptionAnswer(option=0), response_ms=1200)

    assert graded.is_correct is True
    assert graded.response_ms == 1200
    assert graded.answered_at is not None
    assert session.current is None
    assert session.history == [graded]
    assert session.finished_at is None  # open until finished
    assert session.updated_at > NOW
    assert (session.answered, session.score) == (1, 1)


def test_ask_then_answer_again() -> None:
    session = make_session(USER_ID)
    session.answer(1, OptionAnswer(option=0))

    session.ask(make_question(position=99, question_id=50))

    assert session.current is not None
    assert session.current.position == 1  # after the history
    assert session.current.id is None  # the repository gives it one
    _store_current(session, 2)
    wrong = session.answer(2, OptionAnswer(option=2))
    assert wrong.is_correct is False
    assert (session.answered, session.score) == (2, 1)


def test_only_the_active_question_is_answered() -> None:
    session = make_session(USER_ID)
    with pytest.raises(QuestionNotActiveError):
        session.answer(7, OptionAnswer(option=0))
    session.answer(1, OptionAnswer(option=0))
    with pytest.raises(QuestionNotActiveError):  # a double click
        session.answer(1, OptionAnswer(option=0))


def test_one_active_question_at_a_time() -> None:
    session = make_session(USER_ID)
    with pytest.raises(QuestionNotActiveError):
        session.ask(make_question(0))


def test_unknown_option() -> None:
    session = make_session(USER_ID)
    with pytest.raises(InvalidAnswerError):
        session.answer(1, OptionAnswer(option=3))  # 3 options: 0..2
    assert session.current is not None
    assert session.updated_at == NOW


def test_finish_drops_the_active_question() -> None:
    session = make_session(USER_ID)
    session.answer(1, OptionAnswer(option=0))
    session.ask(make_question(0))

    session.finish()

    assert session.is_finished
    assert session.current is None
    assert session.answered == 1
    with pytest.raises(SessionFinishedError):
        session.ask(make_question(0))
    finished_at = session.finished_at
    session.finish()  # again: nothing changes
    assert session.finished_at == finished_at


def test_a_finished_session_takes_no_answers() -> None:
    session = make_session(USER_ID)
    session.finish()
    with pytest.raises(SessionFinishedError):
        session.answer(1, OptionAnswer(option=0))


def test_idle_session_ends_at_its_last_activity() -> None:
    session = make_session(USER_ID)  # last activity: NOW
    assert session.ended_at(NOW + IDLE_TIMEOUT) is None
    assert session.close_if_idle(NOW + IDLE_TIMEOUT) is False

    later = NOW + IDLE_TIMEOUT + timedelta(seconds=1)
    assert session.ended_at(later) == NOW
    assert session.close_if_idle(later) is True
    assert session.finished_at == NOW
    assert session.updated_at == NOW  # closing isn't activity
    assert session.current is None
    assert session.close_if_idle(later) is False  # already closed
