from datetime import timedelta

import pytest
from factories import USER_ID, make_question, make_session

from shodoukan_practice.domain.clock import utc_now
from shodoukan_practice.domain.entities import (
    ExerciseSession,
    OptionAnswer,
    session_end,
)
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
    started = session.updated_at

    graded = session.answer(1, OptionAnswer(option=0), response_ms=1200)

    assert graded.is_correct is True
    assert graded.response_ms == 1200
    assert graded.answered_at is not None
    assert session.current is None
    assert session.history == [graded]
    assert session.finished_at is None  # open until finished
    assert session.updated_at > started
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
    started = session.updated_at
    with pytest.raises(InvalidAnswerError):
        session.answer(1, OptionAnswer(option=3))  # 3 options: 0..2
    assert session.current is not None
    assert session.updated_at == started


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


def test_close_at_last_activity_keeps_the_last_activity() -> None:
    session = make_session(USER_ID)
    last = session.updated_at

    session.close_at_last_activity()

    assert session.finished_at == last
    assert session.updated_at == last  # closing a left session isn't activity
    assert session.current is None
    session.close_at_last_activity()  # again: nothing changes
    assert session.finished_at == last


def test_a_finished_session_takes_no_answers() -> None:
    session = make_session(USER_ID)
    session.finish()
    with pytest.raises(SessionFinishedError):
        session.answer(1, OptionAnswer(option=0))


def test_an_idle_session_takes_no_answers_and_isnt_changed() -> None:
    session = make_session(USER_ID)
    session.updated_at = utc_now() - IDLE_TIMEOUT - timedelta(minutes=1)
    before = session.model_copy(deep=True)

    with pytest.raises(SessionFinishedError):
        session.answer(1, OptionAnswer(option=0))
    session.current = None
    with pytest.raises(SessionFinishedError):
        session.ask(make_question(0))

    session.current = before.current
    assert session == before


def test_idle_session_ends_at_its_last_activity() -> None:
    session = make_session(USER_ID)
    last = session.updated_at
    assert session.ended_at(last + IDLE_TIMEOUT) is None
    assert session.close_if_idle(last + IDLE_TIMEOUT) is False

    later = last + IDLE_TIMEOUT + timedelta(seconds=1)
    assert session.ended_at(later) == last
    assert session.close_if_idle(later) is True
    assert session.finished_at == last
    assert session.updated_at == last  # closing isn't activity
    assert session.current is None
    assert session.close_if_idle(later) is False  # already closed


def test_session_end_is_the_close_or_the_last_activity_once_idle() -> None:
    now = utc_now()
    closed = now - timedelta(hours=1)
    assert session_end(closed, now, now) == closed
    assert session_end(None, now - timedelta(minutes=1), now) is None
    idle_since = now - IDLE_TIMEOUT - timedelta(seconds=1)
    assert session_end(None, idle_since, now) == idle_since
