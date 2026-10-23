import json

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


def test_get_by_id_exposes_jlpt(engine):
    repo = EntryRepository(engine)
    entry = repo.get_by_id(1000001)
    assert entry.jlpt == 5


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


def test_search_by_gloss_phrase(engine):
    repo = EntryRepository(engine)
    page = repo.search_by_gloss("to eat", limit=20, offset=0)
    assert any(e.id == 1000001 for e in page.items)


def test_search_by_gloss_fallback_prefix(engine):
    repo = EntryRepository(engine)
    page = repo.search_by_gloss("water", limit=20, offset=0)
    assert any(e.id == 1000002 for e in page.items)


def test_search_by_gloss_no_results(engine):
    repo = EntryRepository(engine)
    page = repo.search_by_gloss("xyznonexistent", limit=20, offset=0)
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
    page = repo.search_by_gloss("eat", limit=1, offset=0)
    assert len(page.items) <= 1


def test_priority_order(conn, engine):
    conn.execute("INSERT INTO entries VALUES (9999001, NULL, 520, 1)")
    conn.execute(
        "INSERT INTO kanji_readings(entry_id, kanji) VALUES (9999001, '食べる')"
    )
    conn.execute("INSERT INTO entry_kanji VALUES (9999001, '食')")
    conn.execute("INSERT INTO entries VALUES (9999002, NULL, 0, 0)")
    conn.execute(
        "INSERT INTO kanji_readings(entry_id, kanji) VALUES (9999002, '食べる')"
    )
    conn.execute("INSERT INTO entry_kanji VALUES (9999002, '食')")
    conn.commit()

    repo = EntryRepository(engine)
    page = repo.get_entries_for_kanji("食", limit=20, offset=0)
    ids = [e.id for e in page.items]
    assert ids.index(9999001) < ids.index(9999002)


def test_search_by_gloss_lang_es(conn, engine):
    conn.execute("INSERT INTO entries VALUES (9980001, NULL, 0, 0)")
    conn.execute("INSERT INTO readings(entry_id, text) VALUES (9980001, 'たべる')")
    sid = conn.execute(
        "INSERT INTO senses(entry_id, pos) VALUES (9980001, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'comer', 'spa')", (sid,)
    )
    conn.execute("INSERT INTO entry_sense_counts VALUES (9980001, 'spa', 1)")
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'spa', 0)", (sid,))
    conn.commit()

    repo = EntryRepository(engine)
    page = repo.search_by_gloss("comer", lang="es", limit=20, offset=0)
    assert any(e.id == 9980001 for e in page.items)


def test_search_by_gloss_lang_mismatch(conn, engine):
    repo = EntryRepository(engine)
    page = repo.search_by_gloss("comer", lang="en", limit=20, offset=0)
    assert not any(e.id == 9980001 for e in page.items)


def test_gloss_search_orders_by_priority(conn, engine):
    # 9960001: rare word (no priority, no jlpt)
    conn.execute("INSERT INTO entries VALUES (9960001, NULL, 0, 0)")
    conn.execute("INSERT INTO readings(entry_id, text) VALUES (9960001, 'さかな')")
    sid = conn.execute(
        "INSERT INTO senses(entry_id, pos) VALUES (9960001, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'fish', 'eng')", (sid,)
    )
    # 9960002: ichi1 common word — freq_score=510 (500 bonus + 10 for reading ichi1)
    conn.execute("INSERT INTO entries VALUES (9960002, NULL, 510, 1)")
    conn.execute(
        "INSERT INTO readings(entry_id, text, priority) VALUES (9960002, 'さかな', ?)",
        (json.dumps(["ichi1"]),),
    )
    sid2 = conn.execute(
        "INSERT INTO senses(entry_id, pos) VALUES (9960002, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'fish', 'eng')", (sid2,)
    )
    conn.execute("INSERT INTO entry_sense_counts VALUES (9960001, 'eng', 1)")
    conn.execute("INSERT INTO entry_sense_counts VALUES (9960002, 'eng', 1)")
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sid,))
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sid2,))
    conn.commit()

    repo = EntryRepository(engine)
    page = repo.search_by_gloss("fish", limit=20, offset=0)
    ids = [e.id for e in page.items]
    assert ids.index(9960002) < ids.index(9960001)  # ichi1 comes first


def test_gloss_search_total_senses_do_not_penalise(conn, engine, monkeypatch):
    # Only the matched sense's position decays the score, not how many senses
    # the entry has.
    # 9940001: ichi1, 9 senses, match in 1st sense (pos 0)
    conn.execute("INSERT INTO entries VALUES (9940001, NULL, 510, 1)")
    conn.execute(
        "INSERT INTO readings(entry_id, text, priority) VALUES (9940001, 'たべる', ?)",
        (json.dumps(["ichi1"]),),
    )
    sid = conn.execute(
        "INSERT INTO senses(entry_id, pos) VALUES (9940001, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to snack', 'eng')",
        (sid,),
    )
    for _ in range(8):
        extra_sid = conn.execute(
            "INSERT INTO senses(entry_id, pos) VALUES (9940001, '[]')"
        ).lastrowid
        conn.execute(
            "INSERT INTO glosses(sense_id, text, lang)"
            " VALUES (?, 'other meaning', 'eng')",
            (extra_sid,),
        )
    # 9940002: ichi1, 1 sense, match in 1st sense (pos 0)
    conn.execute("INSERT INTO entries VALUES (9940002, NULL, 510, 1)")
    conn.execute(
        "INSERT INTO readings(entry_id, text, priority) VALUES (9940002, 'くう', ?)",
        (json.dumps(["ichi1"]),),
    )
    sid2 = conn.execute(
        "INSERT INTO senses(entry_id, pos) VALUES (9940002, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to snack', 'eng')",
        (sid2,),
    )
    conn.execute("INSERT INTO entry_sense_counts VALUES (9940001, 'eng', 9)")
    conn.execute("INSERT INTO entry_sense_counts VALUES (9940002, 'eng', 1)")
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sid,))
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sid2,))
    conn.commit()

    monkeypatch.setenv("SHODOUKAN_DEBUG", "1")
    repo = EntryRepository(engine)
    page = repo.search_by_gloss("snack", limit=20, offset=0)
    scores = {e.id: e.score for e in page.items}
    # same priority and sense position: same score, 9 senses or 1
    assert scores[9940001].composite == scores[9940002].composite == 510
    assert scores[9940001].score == scores[9940002].score


def test_gloss_search_priority_beats_moderate_sense_penalty(conn, engine):
    # 9950001: ichi1 (high priority), match in 3rd sense (lang_sense_index=2)
    conn.execute("INSERT INTO entries VALUES (9950001, NULL, 510, 1)")
    conn.execute(
        "INSERT INTO readings(entry_id, text, priority) VALUES (9950001, 'とる', ?)",
        (json.dumps(["ichi1"]),),
    )
    sid0 = conn.execute(
        "INSERT INTO senses(entry_id, sense_index, pos) VALUES (9950001, 0, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to take', 'eng')",
        (sid0,),
    )
    sid1 = conn.execute(
        "INSERT INTO senses(entry_id, sense_index, pos) VALUES (9950001, 1, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to get', 'eng')", (sid1,)
    )
    sid_late = conn.execute(
        "INSERT INTO senses(entry_id, sense_index, pos) VALUES (9950001, 2, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to munch', 'eng')",
        (sid_late,),
    )
    # 9950002: no priority, match in 1st sense (lang_sense_index=0)
    conn.execute("INSERT INTO entries VALUES (9950002, NULL, 0, 0)")
    conn.execute("INSERT INTO readings(entry_id, text) VALUES (9950002, 'たべる')")
    sid_first = conn.execute(
        "INSERT INTO senses(entry_id, pos) VALUES (9950002, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to munch', 'eng')",
        (sid_first,),
    )
    conn.execute("INSERT INTO entry_sense_counts VALUES (9950001, 'eng', 3)")
    conn.execute("INSERT INTO entry_sense_counts VALUES (9950002, 'eng', 1)")
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sid0,))
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 1)", (sid1,))
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 2)", (sid_late,))
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sid_first,))
    conn.commit()

    repo = EntryRepository(engine)
    page = repo.search_by_gloss("munch", limit=20, offset=0)
    ids = [e.id for e in page.items]
    # ichi1 priority outweighs a moderate sense-position disadvantage (pos 2)
    assert ids.index(9950001) < ids.index(9950002)


def test_gloss_search_jlpt_ordering(conn, engine):
    # 9930001: ichi1, N3 — same structure as 9930002
    conn.execute("INSERT INTO entries VALUES (9930001, 3, 510, 1)")
    conn.execute(
        "INSERT INTO readings(entry_id, text, priority) VALUES (9930001, 'とぶ', ?)",
        (json.dumps(["ichi1"]),),
    )
    sid = conn.execute(
        "INSERT INTO senses(entry_id, pos) VALUES (9930001, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to hop', 'eng')", (sid,)
    )
    # 9930002: ichi1, N5 — same structure, higher JLPT bonus
    conn.execute("INSERT INTO entries VALUES (9930002, 5, 510, 1)")
    conn.execute(
        "INSERT INTO readings(entry_id, text, priority) VALUES (9930002, 'はねる', ?)",
        (json.dumps(["ichi1"]),),
    )
    sid2 = conn.execute(
        "INSERT INTO senses(entry_id, pos) VALUES (9930002, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to hop', 'eng')", (sid2,)
    )
    conn.execute("INSERT INTO entry_sense_counts VALUES (9930001, 'eng', 1)")
    conn.execute("INSERT INTO entry_sense_counts VALUES (9930002, 'eng', 1)")
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sid,))
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sid2,))
    conn.commit()

    repo = EntryRepository(engine)
    page = repo.search_by_gloss("hop", limit=20, offset=0)
    ids = [e.id for e in page.items]
    assert ids.index(9930002) < ids.index(9930001)  # N5 before N3


def test_japanese_search_jlpt_ordering(conn, engine):
    # 9920001: same reading, N3
    conn.execute("INSERT INTO entries VALUES (9920001, 3, 0, 0)")
    conn.execute("INSERT INTO readings(entry_id, text) VALUES (9920001, 'のぼる')")
    conn.execute("INSERT INTO senses(entry_id, pos) VALUES (9920001, '[]')")
    # 9920002: same reading, N5
    conn.execute("INSERT INTO entries VALUES (9920002, 5, 0, 0)")
    conn.execute("INSERT INTO readings(entry_id, text) VALUES (9920002, 'のぼる')")
    conn.execute("INSERT INTO senses(entry_id, pos) VALUES (9920002, '[]')")
    conn.commit()

    repo = EntryRepository(engine)
    page = repo.search_by_japanese("のぼる", limit=20, offset=0)
    ids = [e.id for e in page.items]
    assert ids.index(9920002) < ids.index(9920001)  # N5 before N3


def test_gloss_search_score_breakdown_in_debug(conn, engine, monkeypatch):
    monkeypatch.setenv("SHODOUKAN_DEBUG", "1")
    repo = EntryRepository(engine)
    page = repo.search_by_gloss("eat")
    assert page.items
    for entry in page.items:
        assert entry.score is not None
        assert entry.score.fts_rank is not None
        assert entry.score.composite is not None
        assert entry.score.freq is not None
        assert entry.score.jlpt_bonus is not None
        assert entry.score.total_senses is not None


def test_japanese_search_score_breakdown_in_debug(conn, engine, monkeypatch):
    monkeypatch.setenv("SHODOUKAN_DEBUG", "1")
    repo = EntryRepository(engine)
    page = repo.search_by_japanese("たべる", 20, 0)
    assert page.items
    for entry in page.items:
        assert entry.score is not None
        assert entry.score.freq is not None
        assert entry.score.jlpt_bonus is not None
        assert entry.score.exact_match is not None


def test_score_breakdown_absent_without_debug(conn, engine, monkeypatch):
    monkeypatch.delenv("SHODOUKAN_DEBUG", raising=False)
    repo = EntryRepository(engine)
    page = repo.search_by_gloss("eat")
    for entry in page.items:
        assert entry.score is None


def test_gloss_search_sense_counts_match_in_first_sense(conn, engine, monkeypatch):
    # ugoku-like: 3 English senses each with multiple glosses, FTS match is 1st sense
    # Verifies total_senses counts senses (not glosses) and sense_pos is 0
    monkeypatch.setenv("SHODOUKAN_DEBUG", "1")
    conn.execute("INSERT INTO entries VALUES (9910001, NULL, 0, 0)")
    conn.execute("INSERT INTO readings(entry_id, text) VALUES (9910001, 'うごく')")
    sid1 = conn.execute(
        "INSERT INTO senses(entry_id, sense_index, pos) VALUES (9910001, 0, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to shimmy', 'eng')",
        (sid1,),
    )
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to sway', 'eng')",
        (sid1,),
    )
    sid2 = conn.execute(
        "INSERT INTO senses(entry_id, sense_index, pos) VALUES (9910001, 1, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to operate', 'eng')",
        (sid2,),
    )
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to work', 'eng')",
        (sid2,),
    )
    sid3 = conn.execute(
        "INSERT INTO senses(entry_id, sense_index, pos) VALUES (9910001, 2, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to function', 'eng')",
        (sid3,),
    )
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to act', 'eng')",
        (sid3,),
    )
    conn.execute("INSERT INTO entry_sense_counts VALUES (9910001, 'eng', 3)")
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sid1,))
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 1)", (sid2,))
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 2)", (sid3,))
    conn.commit()

    repo = EntryRepository(engine)
    page = repo.search_by_gloss("shimmy", limit=20, offset=0)
    entry = next(e for e in page.items if e.id == 9910001)
    assert entry.score.total_senses == 3  # 3 senses, not 6 glosses
    assert entry.score.sense_pos == 0


def test_gloss_search_sense_counts_match_in_third_sense(conn, engine, monkeypatch):
    # hashiru-like: 3 English senses each with multiple glosses, FTS match is 3rd sense
    # Verifies sense_pos counts prior senses (not glosses)
    monkeypatch.setenv("SHODOUKAN_DEBUG", "1")
    conn.execute("INSERT INTO entries VALUES (9910002, NULL, 0, 0)")
    conn.execute("INSERT INTO readings(entry_id, text) VALUES (9910002, 'はしる')")
    sid1 = conn.execute(
        "INSERT INTO senses(entry_id, sense_index, pos) VALUES (9910002, 0, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to run', 'eng')",
        (sid1,),
    )
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to sprint', 'eng')",
        (sid1,),
    )
    sid2 = conn.execute(
        "INSERT INTO senses(entry_id, sense_index, pos) VALUES (9910002, 1, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to dash', 'eng')",
        (sid2,),
    )
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to race', 'eng')",
        (sid2,),
    )
    sid3 = conn.execute(
        "INSERT INTO senses(entry_id, sense_index, pos) VALUES (9910002, 2, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to glide', 'eng')",
        (sid3,),
    )
    conn.execute("INSERT INTO entry_sense_counts VALUES (9910002, 'eng', 3)")
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sid1,))
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 1)", (sid2,))
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 2)", (sid3,))
    conn.commit()

    repo = EntryRepository(engine)
    page = repo.search_by_gloss("glide", limit=20, offset=0)
    entry = next(e for e in page.items if e.id == 9910002)
    assert entry.score.total_senses == 3  # 3 senses, not 5 glosses
    assert entry.score.sense_pos == 2  # two English senses before the match


def test_gloss_search_sense_total_excludes_other_languages(conn, engine, monkeypatch):
    # 2 English senses + 1 Spanish sense; English search must count only 2
    monkeypatch.setenv("SHODOUKAN_DEBUG", "1")
    conn.execute("INSERT INTO entries VALUES (9910003, NULL, 0, 0)")
    conn.execute("INSERT INTO readings(entry_id, text) VALUES (9910003, 'ながれる')")
    sid1 = conn.execute(
        "INSERT INTO senses(entry_id, sense_index, pos) VALUES (9910003, 0, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to drift', 'eng')",
        (sid1,),
    )
    sid2 = conn.execute(
        "INSERT INTO senses(entry_id, sense_index, pos) VALUES (9910003, 1, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'to stream', 'eng')",
        (sid2,),
    )
    sid3 = conn.execute(
        "INSERT INTO senses(entry_id, sense_index, pos) VALUES (9910003, 2, '[]')"
    ).lastrowid
    conn.execute(
        "INSERT INTO glosses(sense_id, text, lang) VALUES (?, 'fluir', 'spa')", (sid3,)
    )
    conn.execute("INSERT INTO entry_sense_counts VALUES (9910003, 'eng', 2)")
    conn.execute("INSERT INTO entry_sense_counts VALUES (9910003, 'spa', 1)")
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 0)", (sid1,))
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', 1)", (sid2,))
    conn.execute("INSERT INTO sense_lang_index VALUES (?, 'spa', 0)", (sid3,))
    conn.commit()

    repo = EntryRepository(engine)
    page = repo.search_by_gloss("drift", lang="en", limit=20, offset=0)
    entry = next(e for e in page.items if e.id == 9910003)
    assert entry.score.total_senses == 2  # Spanish sense not counted
    assert entry.score.sense_pos == 0


def test_gloss_search_sense_position_decays_logarithmically(conn, engine, monkeypatch):
    # Same popularity; the match is in sense 1 for one entry and sense 3 for
    # the other: popularity / log2(pos + 2) -> 1.0 and 0.5.
    for entry_id, match_pos in ((9960001, 0), (9960002, 2)):
        conn.execute(f"INSERT INTO entries VALUES ({entry_id}, NULL, 510, 1)")
        for pos in range(3):
            sid = conn.execute(
                f"INSERT INTO senses(entry_id, pos) VALUES ({entry_id}, '[]')"
            ).lastrowid
            text = "to nibble" if pos == match_pos else f"other meaning {pos}"
            conn.execute(
                "INSERT INTO glosses(sense_id, text, lang) VALUES (?, ?, 'eng')",
                (sid, text),
            )
            conn.execute(
                "INSERT INTO sense_lang_index VALUES (?, 'eng', ?)", (sid, pos)
            )
        conn.execute(f"INSERT INTO entry_sense_counts VALUES ({entry_id}, 'eng', 3)")
    conn.commit()

    monkeypatch.setenv("SHODOUKAN_DEBUG", "1")
    page = EntryRepository(engine).search_by_gloss("nibble", limit=20, offset=0)

    assert [e.id for e in page.items] == [9960001, 9960002]
    first, third = (e.score for e in page.items)
    assert (first.sense_pos, first.composite) == (0, 510)
    assert (third.sense_pos, third.composite) == (2, 255)


# --- Unified search: one score, one query, exact pagination ---


def _add_entry(conn, entry_id, reading, senses, freq=0, jlpt=None):
    """Insert an entry with a kana reading and English glosses per sense."""
    conn.execute(
        "INSERT INTO entries VALUES (?, ?, ?, 0)", (entry_id, jlpt, freq)
    )
    conn.execute(
        "INSERT INTO readings(entry_id, text) VALUES (?, ?)", (entry_id, reading)
    )
    for pos, glosses in enumerate(senses):
        sid = conn.execute(
            "INSERT INTO senses(entry_id, pos) VALUES (?, '[]')", (entry_id,)
        ).lastrowid
        for gloss in glosses:
            conn.execute(
                "INSERT INTO glosses(sense_id, text, lang) VALUES (?, ?, 'eng')",
                (sid, gloss),
            )
        conn.execute("INSERT INTO sense_lang_index VALUES (?, 'eng', ?)", (sid, pos))
    conn.execute(
        "INSERT INTO entry_sense_counts VALUES (?, 'eng', ?)", (entry_id, len(senses))
    )


def test_search_pages_partition_the_results(conn, engine):
    # Readings starting with ぽぽ and glosses with "popo": two kinds of match.
    for i in range(5):
        _add_entry(conn, 9970000 + i, f"ぽぽ{i}", [["something"]], freq=10 * i)
        _add_entry(conn, 9970100 + i, f"べつ{i}", [[f"popo kind {i}"]], freq=10 * i)
    conn.commit()
    repo = EntryRepository(engine)

    full = repo.search(reading_query="ぽぽ", gloss_query="popo", limit=100)
    pages = [
        repo.search(reading_query="ぽぽ", gloss_query="popo", limit=3, offset=offset)
        for offset in (0, 3, 6, 9)
    ]

    assert full.total == 10
    assert all(page.total == 10 for page in pages)
    paged_ids = [e.id for page in pages for e in page.items]
    assert paged_ids == [e.id for e in full.items]
    assert len(set(paged_ids)) == 10


def test_search_counts_an_entry_matched_both_ways_once(conn, engine, monkeypatch):
    monkeypatch.setenv("SHODOUKAN_DEBUG", "1")
    repo = EntryRepository(engine)

    # 1000001 is たべる and has the gloss "to eat".
    page = repo.search(reading_query="たべる", gloss_query="eat", limit=20)

    assert [e.id for e in page.items].count(1000001) == 1
    assert page.total == len({e.id for e in page.items})
    # ...ranked by its reading match
    score = next(e.score for e in page.items if e.id == 1000001)
    assert (score.exact_match, score.fts_rank) == (True, None)


def test_romaji_gloss_of_its_own_reading_ranks_as_the_reading(
    conn, engine, monkeypatch
):
    # 水ようかん: reading みずようかん, gloss "mizu yokan" (its own reading in
    # romaji), not popular. 湖: popular prefix reading. 水絵-like transliterations
    # shouldn't jump over it, but a real translation found only by gloss keeps
    # its gloss tier.
    _add_entry(conn, 9990101, "みずようかん", [["mizu yokan"]], freq=0)
    _add_entry(conn, 9990102, "みずうみ", [["lake"]], freq=520, jlpt=4)
    _add_entry(conn, 9990103, "べつ", [["mizu"]], freq=0)
    conn.commit()
    monkeypatch.setenv("SHODOUKAN_DEBUG", "1")

    page = EntryRepository(engine).search(
        reading_query="みず", gloss_query="mizu", limit=20
    )

    ids = [e.id for e in page.items]
    assert ids.index(9990102) < ids.index(9990101)
    by_id = {e.id: e.score for e in page.items}
    assert by_id[9990101].match_tier == 2  # prefix reading, not a tier-3 gloss
    assert by_id[9990101].exact_match is False
    assert by_id[9990103].match_tier == 3  # found only by gloss


def test_search_past_the_end_still_reports_the_total(conn, engine):
    page = EntryRepository(engine).search(reading_query="たべる", limit=20, offset=50)
    assert page.items == []
    assert page.total == 1


def test_search_without_queries_is_empty(conn, engine):
    page = EntryRepository(engine).search()
    assert (page.items, page.total) == ([], 0)


def test_best_gloss_match_beats_a_more_popular_weak_one(conn, engine, monkeypatch):
    _add_entry(conn, 9980001, "しまうま", [["zebra"]], freq=0)
    _add_entry(
        conn,
        9980002,
        "ほか",
        [["a large striped animal of the savannah somewhat like a zebra"]],
        freq=540,
        jlpt=5,
    )
    conn.commit()
    monkeypatch.setenv("SHODOUKAN_DEBUG", "1")

    page = EntryRepository(engine).search_by_gloss("zebra", limit=20)

    assert [e.id for e in page.items] == [9980001, 9980002]
    best, weak = (e.score for e in page.items)
    assert (best.match_tier, best.relevance) == (3, 1.0)
    assert weak.match_tier < 3


def test_exact_reading_beats_a_more_popular_prefix(conn, engine, monkeypatch):
    _add_entry(conn, 9980101, "ふぉお", [["rare"]], freq=0)
    _add_entry(conn, 9980102, "ふぉおく", [["fork"]], freq=540, jlpt=5)
    conn.commit()
    monkeypatch.setenv("SHODOUKAN_DEBUG", "1")

    page = EntryRepository(engine).search_by_japanese("ふぉお", 20, 0)

    assert [e.id for e in page.items] == [9980101, 9980102]
    assert [e.score.match_tier for e in page.items] == [3, 2]
    assert page.items[0].score.score == 3 * 2000 + 0


def test_equal_scores_are_ordered_by_id(conn, engine):
    for entry_id in (9990003, 9990001, 9990002):
        _add_entry(conn, entry_id, "ぴよ", [["chirp"]], freq=100)
    conn.commit()

    page = EntryRepository(engine).search_by_japanese("ぴよ", 20, 0)

    assert [e.id for e in page.items] == [9990001, 9990002, 9990003]


def test_unified_score_breakdown_in_debug(conn, engine, monkeypatch):
    monkeypatch.setenv("SHODOUKAN_DEBUG", "1")

    page = EntryRepository(engine).search(
        reading_query="たべる", gloss_query="water", limit=20
    )

    by_id = {e.id: e.score for e in page.items}
    reading, gloss = by_id[1000001], by_id[1000002]
    assert (reading.match_tier, reading.exact_match) == (3, True)
    assert reading.fts_rank is None
    assert reading.score == 3 * 2000 + reading.freq + reading.jlpt_bonus
    assert gloss.fts_rank is not None and gloss.relevance == 1.0
    assert gloss.score == gloss.match_tier * 2000 + gloss.composite
