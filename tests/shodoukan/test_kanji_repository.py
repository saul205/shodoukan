import json

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


def test_search_by_on_reading_in_hiragana(engine):
    # KANJIDIC2 stores on-readings in katakana (スイ); kana input is hiragana.
    repo = KanjiRepository(engine)
    page = repo.search(query="すい", grade=None, jlpt=None, limit=20, offset=0)
    assert [k.literal for k in page.items] == ["水"]


def test_search_by_on_reading_prefix_in_hiragana(engine):
    repo = KanjiRepository(engine)
    page = repo.search(query="しょ", grade=None, jlpt=None, limit=20, offset=0)
    assert [k.literal for k in page.items] == ["食"]


def test_search_by_kun_reading_in_katakana(engine):
    repo = KanjiRepository(engine)
    page = repo.search(query="ミズ", grade=None, jlpt=None, limit=20, offset=0)
    assert [k.literal for k in page.items] == ["水"]


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


# --- Ranked search (tiers) ----------------------------------------------------


def _add_kanji(conn, literal, jlpt, freq, on=(), kun=(), meanings=()):
    conn.execute(
        "INSERT INTO kanji(literal, grade, stroke_count, freq, jlpt,"
        " on_readings, kun_readings) VALUES (?, NULL, 1, ?, ?, ?, ?)",
        (literal, freq, jlpt, json.dumps(list(on)), json.dumps(list(kun))),
    )
    for meaning in meanings:
        conn.execute(
            "INSERT INTO kanji_meanings(literal, text, lang) VALUES (?, ?, 'en')",
            (literal, meaning),
        )


@pytest.fixture
def ranked_repo(conn, engine):
    # "au" (あう): 合 is read あう; 図 and 秋 only share the prefix "au" with
    # "audacious" / "autumn", and both are more popular than 合.
    _add_kanji(conn, "合", 3, 41, on=["ゴウ"], kun=["あ.う"], meanings=["fit"])
    _add_kanji(conn, "図", 4, 539, on=["ズ"], meanings=["map", "audacious"])
    _add_kanji(conn, "秋", 4, 635, on=["シュウ"], meanings=["autumn"])
    # "same" (さめ): 同 means "same", 鮫 is read さめ, 偶 contains "same".
    _add_kanji(conn, "同", 4, 15, on=["ドウ"], kun=["おな.じ"], meanings=["same"])
    _add_kanji(conn, "鮫", None, 2244, on=["コウ"], kun=["さめ"], meanings=["shark"])
    _add_kanji(conn, "偶", 3, 1210, on=["グウ"], meanings=["the same kind"])
    conn.commit()
    return KanjiRepository(engine)


def _literals(page):
    return [k.literal for k in page.items]


def test_ranked_exact_reading_beats_meaning_prefix(ranked_repo):
    page = ranked_repo.search_ranked(reading_query="あう", meaning_query="au")
    assert _literals(page) == ["合", "図", "秋"]
    assert page.total == 3


def test_ranked_exact_meaning_and_exact_reading_share_a_tier(ranked_repo):
    # 同 and 鮫 are both tier 3 and ordered by popularity; 偶 only contains
    # "same", so it comes after 鮫 although it is more popular.
    page = ranked_repo.search_ranked(reading_query="さめ", meaning_query="same")
    assert _literals(page) == ["同", "鮫", "偶"]


def test_ranked_kanji_found_both_ways_counts_once(ranked_repo):
    page = ranked_repo.search_ranked(reading_query="おなじ", meaning_query="same")
    assert _literals(page).count("同") == 1
    assert page.total == len(page.items) == 2


def test_ranked_pages_partition_the_results(ranked_repo):
    query = {"reading_query": "さめ", "meaning_query": "same"}
    full = _literals(ranked_repo.search_ranked(**query))
    pages = [
        ranked_repo.search_ranked(**query, limit=1, offset=offset)
        for offset in range(len(full))
    ]
    assert [lit for p in pages for lit in _literals(p)] == full
    assert all(p.total == len(full) for p in pages)


def test_ranked_past_the_end_keeps_the_total(ranked_repo):
    page = ranked_repo.search_ranked(
        reading_query="あう", meaning_query="au", offset=10
    )
    assert page.items == []
    assert page.total == 3


def test_meaning_search_ranks_exact_meaning_first(ranked_repo):
    page = ranked_repo.search(query="same", grade=None, jlpt=None, limit=20, offset=0)
    assert _literals(page) == ["同", "偶"]


def test_get_strokes_in_writing_order(engine):
    strokes = KanjiRepository(engine).get_strokes("食")

    assert strokes is not None
    assert strokes.literal == "食"
    # Ordered by stroke number, not by where they sit in the SVG.
    assert [s.path for s in strokes.strokes] == [
        "M54,10c0,5-20,20-40,25",
        "M20,30c10,0,20,0,30,0",
    ]
    assert [s.label for s in strokes.strokes] == [(1.5, 1.0), (2.5, 2.0)]


def test_get_strokes_of_a_compatibility_ideograph(engine):
    # 神 U+FA19 is drawn with its canonical form, 神 U+795E, but keeps its literal.
    strokes = KanjiRepository(engine).get_strokes("神")

    assert strokes is not None
    assert strokes.literal == "神"
    assert len(strokes.strokes) == 1


def test_get_strokes_missing(engine):
    assert KanjiRepository(engine).get_strokes("水") is None
