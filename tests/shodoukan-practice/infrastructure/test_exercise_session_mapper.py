import pytest
from factories import (
    USER_ID,
    make_grade,
    make_handwriting_question,
    make_question,
    make_session,
)

from shodoukan_practice.domain.entities import OptionAnswer, SkipAnswer, StrokesAnswer
from shodoukan_practice.infrastructure.db.mappers import (
    exercise_session_to_db,
    exercise_session_to_domain,
)


def test_round_trip_keeps_the_session() -> None:
    session = make_session(USER_ID, exercise_id=4, item_id=7)
    session.answer(1, OptionAnswer(option=2), response_ms=900)
    session.ask(make_question(0, item_id=8, question_id=2))
    assert exercise_session_to_domain(exercise_session_to_db(session)) == session


def test_history_and_the_active_question_share_the_table() -> None:
    session = make_session(USER_ID, item_id=7)
    session.answer(1, OptionAnswer(option=0))
    session.ask(make_question(0, item_id=8))

    row = exercise_session_to_db(session)

    assert [(q.position, q.kanji_id, q.answer is None) for q in row.questions] == [
        (0, 7, False),
        (1, 8, True),  # the active one: no answer
    ]
    back = exercise_session_to_domain(row)
    assert [q.item_id for q in back.history] == [7]
    assert back.current is not None
    assert back.current.item_id == 8


def test_item_goes_to_the_column_of_its_kind() -> None:
    kanji = exercise_session_to_db(make_session(USER_ID, item_id=7))
    assert (kanji.questions[0].kanji_id, kanji.questions[0].entry_id) == (7, None)

    words = make_session(USER_ID, item_id=7)
    words.item_kind = "entries"
    row = exercise_session_to_db(words)
    assert (row.questions[0].entry_id, row.questions[0].kanji_id) == (7, None)


def test_snapshot_is_plain_json() -> None:
    row = exercise_session_to_db(make_session(USER_ID, item_id=7)).questions[0]
    assert row.prompt == [{"field": "literal", "values": ["食"]}]
    assert row.type == "card.choice"
    assert row.details["options"][0] == {"text": "た.べる", "item_id": 7}
    assert row.details["correct_option"] == 0
    assert row.answer is None


def test_round_trip_keeps_a_skipped_question() -> None:
    session = make_session(USER_ID, item_id=7)
    session.answer(1, SkipAnswer())

    row = exercise_session_to_db(session)

    assert row.questions[0].answer == {"type": "skip"}
    assert exercise_session_to_domain(row) == session


def test_round_trip_keeps_a_handwriting_question() -> None:
    session = make_session(USER_ID, item_id=7, handwriting=True)
    drawing = StrokesAnswer(strokes=(((10.0, 54.0), (90.5, 52.25)),))
    session.answer(1, drawing, response_ms=4000, grade=make_grade("close"))
    session.ask(make_handwriting_question(0, item_id=8, question_id=2))

    row = exercise_session_to_db(session)

    answered = row.questions[0]
    assert answered.type == "card.handwriting"
    assert set(answered.details) == {"references", "grade"}
    assert answered.details["grade"]["verdict"] == "close"
    assert answered.answer == {
        "type": "strokes",
        "strokes": [[[10.0, 54.0], [90.5, 52.25]]],
    }
    assert row.questions[1].details["grade"] is None
    assert exercise_session_to_domain(row) == session


def test_an_unknown_question_type_is_refused() -> None:
    row = exercise_session_to_db(make_session(USER_ID, item_id=7))
    row.questions[0].type = "card.flip"

    with pytest.raises(ValueError, match="unknown question type"):
        exercise_session_to_domain(row)
