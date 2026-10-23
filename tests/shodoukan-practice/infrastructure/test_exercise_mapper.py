from factories import USER_ID, make_entry_exercise, make_kanji_exercise

from shodoukan_practice.infrastructure.db.mappers import (
    exercise_to_db,
    exercise_to_domain,
)


def test_round_trip_keeps_the_entity() -> None:
    for exercise in (
        make_entry_exercise(USER_ID, (3, 1)),
        make_kanji_exercise(USER_ID, (2,)),
    ):
        assert exercise_to_domain(exercise_to_db(exercise)) == exercise


def test_collections_go_to_the_link_table_of_their_kind() -> None:
    entry_row = exercise_to_db(make_entry_exercise(USER_ID, (3, 1)))
    assert entry_row.item_kind == "entries"
    assert [
        (link.collection_id, link.position) for link in entry_row.entry_collections
    ] == [
        (3, 0),
        (1, 1),
    ]
    assert entry_row.kanji_collections == []

    kanji_row = exercise_to_db(make_kanji_exercise(USER_ID, (2,)))
    assert kanji_row.item_kind == "kanji"
    assert [link.collection_id for link in kanji_row.kanji_collections] == [2]
    assert kanji_row.entry_collections == []


def test_settings_are_stored_as_plain_json() -> None:
    row = exercise_to_db(make_entry_exercise(USER_ID))
    assert row.settings == {
        "type": "card.choice",
        "directions": [
            {"prompt": ["meaning"], "answer": "writing"},
            {"prompt": ["writing"], "answer": "meaning"},
        ],
        "back_fields": ["reading"],
        "option_count": 4,
        "distractor_source": "collection",
    }
