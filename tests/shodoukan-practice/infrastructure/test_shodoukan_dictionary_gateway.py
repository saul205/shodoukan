from shodoukan import Dictionary
from shodoukan_practice.infrastructure.dictionary import ShodoukanDictionaryGateway


def test_new_practice_entry_from_the_dictionary(dictionary: Dictionary) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)

    entry = gateway.new_practice_entry(1000001, user_id=1)

    assert entry is not None
    assert entry.source_entry_id == 1000001
    assert entry.user_id == 1
    assert [kr.kanji for kr in entry.kanji_readings] == ["食べる"]
    assert [g.text for g in entry.senses[0].glosses] == ["to eat", "to have a meal"]


def test_unknown_entry_is_none(dictionary: Dictionary) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)
    assert gateway.new_practice_entry(999, user_id=1) is None


def test_new_practice_kanji_from_the_dictionary(dictionary: Dictionary) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)

    kanji = gateway.new_practice_kanji("食", user_id=1)

    assert kanji is not None
    assert [r.text for r in kanji.on_readings] == ["ショク", "ジキ"]
    assert [m.text for m in kanji.meanings] == ["eat", "food"]


def test_unknown_kanji_is_none(dictionary: Dictionary) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)
    assert gateway.new_practice_kanji("龘", user_id=1) is None
