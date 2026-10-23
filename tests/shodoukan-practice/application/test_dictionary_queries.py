import pytest

from shodoukan import Dictionary
from shodoukan_practice.application.queries import (
    GetDictionaryEntry,
    GetDictionaryKanji,
    GetDictionaryKanjiStrokes,
    ListEntriesForKanji,
    ListKanjiForEntry,
)
from shodoukan_practice.domain.exceptions import DictionaryItemNotFoundError
from shodoukan_practice.infrastructure.dictionary import ShodoukanDictionaryGateway


@pytest.fixture
def gateway(dictionary: Dictionary) -> ShodoukanDictionaryGateway:
    return ShodoukanDictionaryGateway(dictionary)


def test_get_entry_and_kanji(gateway: ShodoukanDictionaryGateway) -> None:
    assert GetDictionaryEntry(gateway).execute(1000002).kanji_readings[0].kanji == "水"
    assert GetDictionaryKanji(gateway).execute("水").stroke_count == 4


def test_missing_items_raise(gateway: ShodoukanDictionaryGateway) -> None:
    with pytest.raises(DictionaryItemNotFoundError):
        GetDictionaryEntry(gateway).execute(999)
    with pytest.raises(DictionaryItemNotFoundError):
        GetDictionaryKanji(gateway).execute("龘")
    with pytest.raises(DictionaryItemNotFoundError):
        ListEntriesForKanji(gateway).execute("龘")
    with pytest.raises(DictionaryItemNotFoundError):
        ListKanjiForEntry(gateway).execute(999)
    with pytest.raises(DictionaryItemNotFoundError):
        GetDictionaryKanjiStrokes(gateway).execute("水")  # a kanji with no drawing


def test_related_lists(gateway: ShodoukanDictionaryGateway) -> None:
    words = ListEntriesForKanji(gateway).execute("水", limit=5)
    kanji = ListKanjiForEntry(gateway).execute(1000002)

    assert [e.id for e in words.items] == [1000002]
    assert words.limit == 5
    assert [k.literal for k in kanji] == ["水"]


def test_kanji_strokes_need_only_a_drawing(gateway: ShodoukanDictionaryGateway) -> None:
    # 神 isn't a dictionary kanji in the test data, but it has a drawing.
    strokes = GetDictionaryKanjiStrokes(gateway).execute("\u795e")
    assert len(strokes.strokes) == 1
