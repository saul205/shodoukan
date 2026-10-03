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
