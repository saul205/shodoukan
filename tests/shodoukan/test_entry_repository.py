from shodoukan.repositories.entry import EntryRepository


def test_get_by_id_returns_entry(conn):
    repo = EntryRepository(conn)
    entry = repo.get_by_id(1000001)
    assert entry is not None
    assert entry.id == 1000001
    assert len(entry.kanji_readings) == 1
    assert entry.kanji_readings[0].kanji == "食べる"
    assert len(entry.readings) == 1
    assert entry.readings[0].text == "たべる"
    assert len(entry.senses) == 1
    assert any(g.text == "to eat" for g in entry.senses[0].glosses)


def test_get_by_id_returns_none_for_missing(conn):
    repo = EntryRepository(conn)
    assert repo.get_by_id(9999999) is None


def test_search_by_japanese_kanji(conn):
    repo = EntryRepository(conn)
    page = repo.search_by_japanese("食べる", limit=20, offset=0)
    assert page.total >= 1
    assert any(e.id == 1000001 for e in page.items)


def test_search_by_japanese_kana_exact(conn):
    repo = EntryRepository(conn)
    page = repo.search_by_japanese("みず", limit=20, offset=0)
    assert any(e.id == 1000002 for e in page.items)


def test_search_by_japanese_kana_prefix(conn):
    repo = EntryRepository(conn)
    page = repo.search_by_japanese("たべ", limit=20, offset=0)
    assert any(e.id == 1000001 for e in page.items)


def test_search_by_english_phrase(conn):
    repo = EntryRepository(conn)
    page = repo.search_by_english("to eat", limit=20, offset=0)
    assert any(e.id == 1000001 for e in page.items)


def test_search_by_english_fallback_prefix(conn):
    repo = EntryRepository(conn)
    page = repo.search_by_english("water", limit=20, offset=0)
    assert any(e.id == 1000002 for e in page.items)


def test_search_by_english_no_results(conn):
    repo = EntryRepository(conn)
    page = repo.search_by_english("xyznonexistent", limit=20, offset=0)
    assert page.total == 0
    assert page.items == []


def test_get_kanji_for_entry(conn):
    repo = EntryRepository(conn)
    links = repo.get_kanji_for_entry(1000001)
    assert any(lk.literal == "食" for lk in links)


def test_get_entries_for_kanji(conn):
    repo = EntryRepository(conn)
    page = repo.get_entries_for_kanji("食", limit=20, offset=0)
    assert page.total >= 1
    assert any(e.id == 1000001 for e in page.items)


def test_pagination_limit(conn):
    repo = EntryRepository(conn)
    page = repo.search_by_english("eat", limit=1, offset=0)
    assert len(page.items) <= 1


def test_priority_order(conn):
    repo = EntryRepository(conn)
    page = repo.get_entries_for_kanji("食", limit=20, offset=0)
    scores = [
        next(lk.priority_score for lk in repo.get_kanji_for_entry(e.id) if lk.literal == "食")
        for e in page.items
    ]
    assert scores == sorted(scores, reverse=True)
