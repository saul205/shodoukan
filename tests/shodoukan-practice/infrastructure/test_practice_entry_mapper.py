from factories import USER_ID, make_entry

from shodoukan_practice.infrastructure.db.mappers import (
    practice_entry_to_db,
    practice_entry_to_domain,
)


def test_round_trip_keeps_the_entity() -> None:
    entry = make_entry(user_id=USER_ID)
    assert practice_entry_to_domain(practice_entry_to_db(entry)) == entry


def test_list_order_becomes_position() -> None:
    row = practice_entry_to_db(make_entry(user_id=USER_ID))
    assert [r.position for r in row.readings] == [0, 1]
    assert [s.position for s in row.senses[0].examples[0].sentences] == [0, 1]


def test_round_trip_keeps_notes() -> None:
    entry = make_entry(user_id=USER_ID)
    entry.notes = "irregular in Kansai"
    entry.senses[0].notes = "only for people"

    row = practice_entry_to_db(entry)

    assert (row.notes, row.senses[0].notes) == (
        "irregular in Kansai",
        "only for people",
    )
    assert practice_entry_to_domain(row) == entry
