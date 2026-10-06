from factories import USER_ID

from shodoukan import Dictionary
from shodoukan_practice.infrastructure.dictionary import ShodoukanDictionaryGateway


def test_new_practice_entry_from_the_dictionary(dictionary: Dictionary) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)

    entry = gateway.new_practice_entry(1000001, user_id=USER_ID)

    assert entry is not None
    assert entry.source_entry_id == 1000001
    assert entry.user_id == USER_ID
    assert [kr.kanji for kr in entry.kanji_readings] == ["食べる"]
    assert [g.text for g in entry.senses[0].glosses] == ["to eat", "to have a meal"]


def test_unknown_entry_is_none(dictionary: Dictionary) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)
    assert gateway.new_practice_entry(999, user_id=USER_ID) is None


def test_new_practice_kanji_from_the_dictionary(dictionary: Dictionary) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)

    kanji = gateway.new_practice_kanji("食", user_id=USER_ID)

    assert kanji is not None
    assert [r.text for r in kanji.on_readings] == ["ショク", "ジキ"]
    assert [m.text for m in kanji.meanings] == ["eat", "food"]


def test_unknown_kanji_is_none(dictionary: Dictionary) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)
    assert gateway.new_practice_kanji("龘", user_id=USER_ID) is None


def test_search_by_japanese(dictionary: Dictionary) -> None:
    result = ShodoukanDictionaryGateway(dictionary).search(
        "食べる", lang="en", limit=20, offset=0
    )

    assert [e.id for e in result.entries.items] == [1000001]
    assert result.entries.total == 1


def test_search_by_romaji_and_by_meaning(dictionary: Dictionary) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)

    by_romaji = gateway.search("taberu", lang="en", limit=20, offset=0)
    by_meaning = gateway.search("water", lang="en", limit=20, offset=0)

    assert 1000001 in [e.id for e in by_romaji.entries.items]
    assert [e.id for e in by_meaning.entries.items] == [1000002]
    assert "水" in [k.literal for k in by_meaning.kanji]


def test_get_entry_and_kanji(dictionary: Dictionary) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)

    entry = gateway.get_entry(1000001)
    kanji = gateway.get_kanji("食")

    assert entry is not None
    assert [r.text for r in entry.readings] == ["たべる"]
    assert kanji is not None
    assert [m.text for m in kanji.meanings] == ["eat", "food"]
    assert gateway.get_entry(999) is None
    assert gateway.get_kanji("龘") is None


def test_entries_for_kanji(dictionary: Dictionary) -> None:
    page = ShodoukanDictionaryGateway(dictionary).entries_for_kanji("食", 10, 0)

    assert [e.id for e in page.items] == [1000001]
    assert (page.total, page.limit, page.offset) == (1, 10, 0)


def test_kanji_for_entry(dictionary: Dictionary) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)

    assert [k.literal for k in gateway.kanji_for_entry(1000001)] == ["食"]
    assert gateway.kanji_for_entry(1000003) == []  # kana only


def test_kanji_strokes(dictionary: Dictionary) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)

    strokes = gateway.kanji_strokes("食")

    assert strokes is not None
    assert [s.path for s in strokes.strokes] == [
        "M54,10c0,5-20,20-40,25",
        "M20,30c10,0,20,0,30,0",
    ]
    assert strokes.strokes[0].label == (1.5, 1.0)
    assert gateway.kanji_strokes("水") is None  # no drawing
