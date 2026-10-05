from factories import USER_ID, make_question, make_session

from shodoukan_practice.domain.entities import OptionAnswer, SkipAnswer
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
    assert row.options[0] == {"text": "た.べる", "item_id": 7}
    assert row.answer is None


def test_round_trip_keeps_a_skipped_question() -> None:
    session = make_session(USER_ID, item_id=7)
    session.answer(1, SkipAnswer())

    row = exercise_session_to_db(session)

    assert row.questions[0].answer == {"type": "skip"}
    assert exercise_session_to_domain(row) == session
