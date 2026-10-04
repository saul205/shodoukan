from factories import USER_ID, make_session

from shodoukan_practice.domain.entities import OptionAnswer
from shodoukan_practice.infrastructure.db.mappers import (
    exercise_session_to_db,
    exercise_session_to_domain,
)


def test_round_trip_keeps_the_session() -> None:
    session = make_session(USER_ID, exercise_id=4, questions=2, item_ids=(7, None))
    session.answer(1, OptionAnswer(option=2), response_ms=900)
    assert exercise_session_to_domain(exercise_session_to_db(session)) == session


def test_item_goes_to_the_column_of_its_kind() -> None:
    kanji = exercise_session_to_db(make_session(USER_ID, item_ids=(7,)))
    assert (kanji.questions[0].kanji_id, kanji.questions[0].entry_id) == (7, None)

    words = make_session(USER_ID, item_ids=(7,))
    words.item_kind = "entries"
    row = exercise_session_to_db(words)
    assert (row.questions[0].entry_id, row.questions[0].kanji_id) == (7, None)


def test_snapshot_is_plain_json() -> None:
    row = exercise_session_to_db(make_session(USER_ID, item_ids=(7,))).questions[0]
    assert row.prompt == [{"field": "literal", "values": ["食"]}]
    assert row.options[0] == {"text": "た.べる", "item_id": 7}
    assert row.answer is None
