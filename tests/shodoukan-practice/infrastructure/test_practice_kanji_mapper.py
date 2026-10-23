from factories import USER_ID, make_kanji

from shodoukan_practice.infrastructure.db.mappers import (
    practice_kanji_to_db,
    practice_kanji_to_domain,
)


def test_round_trip_keeps_the_entity() -> None:
    kanji = make_kanji(user_id=USER_ID)
    assert practice_kanji_to_domain(practice_kanji_to_db(kanji)) == kanji


def test_readings_share_one_table_by_kind() -> None:
    row = practice_kanji_to_db(make_kanji(user_id=USER_ID))
    assert [(i.kind, i.position, i.text) for i in row.reading_items] == [
        ("on", 0, "ショク"),
        ("kun", 0, "た.べる"),
        ("kun", 1, "く.う"),
    ]


def test_round_trip_keeps_notes() -> None:
    kanji = make_kanji(user_id=USER_ID)
    kanji.notes = "looks like 良"
    assert practice_kanji_to_domain(practice_kanji_to_db(kanji)) == kanji


def test_round_trip_keeps_provenance() -> None:
    kanji = make_kanji(user_id=USER_ID)
    kanji.meanings[1].original_id = 5
    kanji.meanings[1].source_id = 6
    kanji.meanings[1].edited_id = 7
    assert practice_kanji_to_domain(practice_kanji_to_db(kanji)) == kanji
