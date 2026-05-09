import pytest
from shodoukan.repositories.kanji import KanjiRepository


def test_get_by_literal(engine):
    repo = KanjiRepository(engine)
    kanji = repo.get_by_literal("食")
    assert kanji is not None
    assert kanji.literal == "食"
    assert kanji.grade == 2
    assert kanji.stroke_count == 9
    assert "ショク" in kanji.on_readings
    assert any(m.text == "eat" for m in kanji.meanings)


def test_get_by_literal_missing(engine):
    repo = KanjiRepository(engine)
    assert repo.get_by_literal("X") is None


def test_search_by_single_kanji_char(engine):
    repo = KanjiRepository(engine)
    page = repo.search(query="食", grade=None, jlpt=None, limit=20, offset=0)
    assert page.total == 1
    assert page.items[0].literal == "食"


def test_search_by_on_reading(engine):
    repo = KanjiRepository(engine)
    page = repo.search(query="スイ", grade=None, jlpt=None, limit=20, offset=0)
    assert any(k.literal == "水" for k in page.items)


def test_search_by_kun_reading(engine):
    repo = KanjiRepository(engine)
    page = repo.search(query="みず", grade=None, jlpt=None, limit=20, offset=0)
    assert any(k.literal == "水" for k in page.items)


def test_search_by_kun_reading_prefix(engine):
    repo = KanjiRepository(engine)
    # "た.べる" should match via okurigana prefix
    page = repo.search(query="た", grade=None, jlpt=None, limit=20, offset=0)
    assert any(k.literal == "食" for k in page.items)


def test_search_by_meaning(engine):
    repo = KanjiRepository(engine)
    page = repo.search(query="water", grade=None, jlpt=None, limit=20, offset=0)
    assert any(k.literal == "水" for k in page.items)


def test_search_by_meaning_partial(engine):
    repo = KanjiRepository(engine)
    page = repo.search(query="eat", grade=None, jlpt=None, limit=20, offset=0)
    assert any(k.literal == "食" for k in page.items)


def test_filter_by_grade(engine):
    repo = KanjiRepository(engine)
    page = repo.search(query=None, grade=1, jlpt=None, limit=20, offset=0)
    assert all(k.grade == 1 for k in page.items)
    assert any(k.literal == "水" for k in page.items)


def test_filter_by_jlpt(engine):
    repo = KanjiRepository(engine)
    page = repo.search(query=None, grade=None, jlpt=4, limit=20, offset=0)
    assert all(k.jlpt == 4 for k in page.items)


def test_filter_grade_and_query(engine):
    repo = KanjiRepository(engine)
    page = repo.search(query="eat", grade=2, jlpt=None, limit=20, offset=0)
    assert any(k.literal == "食" for k in page.items)
    assert all(k.grade == 2 for k in page.items)


def test_no_results(engine):
    repo = KanjiRepository(engine)
    page = repo.search(query="xyznonexistent", grade=None, jlpt=None, limit=20, offset=0)
    assert page.total == 0
    assert page.items == []
