from shodoukan.repositories.entry import EntryRepository


def test_get_by_id_returns_entry(engine):
    repo = EntryRepository(engine)
    entry = repo.get_by_id(1000001)
    assert entry is not None
    assert entry.id == 1000001
    assert len(entry.kanji_readings) == 1
    assert entry.kanji_readings[0].kanji == "食べる"
    assert len(entry.readings) == 1
    assert entry.readings[0].text == "たべる"
    assert len(entry.senses) == 1
    assert any(g.text == "to eat" for g in entry.senses[0].glosses)


def test_get_by_id_returns_none_for_missing(engine):
    repo = EntryRepository(engine)
    assert repo.get_by_id(9999999) is None


def test_search_by_japanese_kanji(engine):
    repo = EntryRepository(engine)
    page = repo.search_by_japanese("食べる", limit=20, offset=0)
    assert page.total >= 1
    assert any(e.id == 1000001 for e in page.items)


def test_search_by_japanese_kana_exact(engine):
    repo = EntryRepository(engine)
    page = repo.search_by_japanese("みず", limit=20, offset=0)
    assert any(e.id == 1000002 for e in page.items)


def test_search_by_japanese_kana_prefix(engine):
    repo = EntryRepository(engine)
    page = repo.search_by_japanese("たべ", limit=20, offset=0)
    assert any(e.id == 1000001 for e in page.items)


def test_search_by_english_phrase(engine):
    repo = EntryRepository(engine)
    page = repo.search_by_english("to eat", limit=20, offset=0)
    assert any(e.id == 1000001 for e in page.items)


def test_search_by_english_fallback_prefix(engine):
    repo = EntryRepository(engine)
    page = repo.search_by_english("water", limit=20, offset=0)
    assert any(e.id == 1000002 for e in page.items)


def test_search_by_english_no_results(engine):
    repo = EntryRepository(engine)
    page = repo.search_by_english("xyznonexistent", limit=20, offset=0)
    assert page.total == 0
    assert page.items == []


def test_get_kanji_for_entry(engine):
    repo = EntryRepository(engine)
    links = repo.get_kanji_for_entry(1000001)
    assert any(lk.literal == "食" for lk in links)


def test_get_entries_for_kanji(engine):
    repo = EntryRepository(engine)
    page = repo.get_entries_for_kanji("食", limit=20, offset=0)
    assert page.total >= 1
    assert any(e.id == 1000001 for e in page.items)


def test_pagination_limit(engine):
    repo = EntryRepository(engine)
    page = repo.search_by_english("eat", limit=1, offset=0)
    assert len(page.items) <= 1


def test_priority_order(engine):
    repo = EntryRepository(engine)
    page = repo.get_entries_for_kanji("食", limit=20, offset=0)
    scores = [
        next(lk.priority_score for lk in repo.get_kanji_for_entry(e.id) if lk.literal == "食")
        for e in page.items
    ]
    assert scores == sorted(scores, reverse=True)


def test_japanese_search_orders_by_priority(conn, engine):
    import json
    # Entry 9990001: common word (ichi1 priority)
    conn.execute("INSERT INTO entries VALUES (9990001)")
    conn.execute(
        "INSERT INTO readings(entry_id, text, priority) VALUES (9990001, 'さかな', ?)",
        (json.dumps(["ichi1"]),),
    )
    conn.execute("INSERT INTO senses(entry_id, pos) VALUES (9990001, '[]')")
    # Entry 9990002: rare word (no priority)
    conn.execute("INSERT INTO entries VALUES (9990002)")
    conn.execute("INSERT INTO readings(entry_id, text) VALUES (9990002, 'さかな')")
    conn.execute("INSERT INTO senses(entry_id, pos) VALUES (9990002, '[]')")
    conn.commit()

    repo = EntryRepository(engine)
    page = repo.search_by_japanese("さかな", limit=20, offset=0)
    ids = [e.id for e in page.items]
    assert ids.index(9990001) < ids.index(9990002)  # ichi1 comes first
