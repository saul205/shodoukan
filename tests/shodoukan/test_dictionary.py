import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from shodoukan.dictionary import Dictionary


@pytest.fixture
def dictionary(conn, tmp_path):
    db_file = tmp_path / "test.sqlite"
    # Write the in-memory DB to a temp file so Dictionary can open it
    backup = sqlite3.connect(str(db_file))
    conn.backup(backup)
    backup.close()

    with patch("shodoukan.dictionary.download"):
        d = Dictionary(db_path=db_file, auto_download=False)
    yield d
    d.close()


def test_get_entry(dictionary):
    entry = dictionary.get_entry(1000001)
    assert entry is not None
    assert entry.id == 1000001


def test_get_entry_missing(dictionary):
    assert dictionary.get_entry(9999999) is None


def test_search_entries_routes_japanese(dictionary):
    page = dictionary.search_entries("食べる")
    assert any(e.id == 1000001 for e in page.items)


def test_search_entries_routes_kana(dictionary):
    page = dictionary.search_entries("みず")
    assert any(e.id == 1000002 for e in page.items)


def test_search_entries_routes_english(dictionary):
    page = dictionary.search_entries("to eat")
    assert any(e.id == 1000001 for e in page.items)


def test_search_entries_routes_romaji(dictionary):
    page = dictionary.search_entries("taberu")
    assert any(e.id == 1000001 for e in page.items)


def test_search_entries_romaji_falls_back_to_english(dictionary):
    # "water" contains 'w' which can't be fully converted to hiragana
    page = dictionary.search_entries("water")
    assert any(e.id == 1000002 for e in page.items)


def test_search_routes_romaji(dictionary):
    result = dictionary.search("taberu")
    assert any(e.id == 1000001 for e in result.entries.items)


def test_get_kanji_for_entry(dictionary):
    links = dictionary.get_kanji_for_entry(1000001)
    assert any(lk.literal == "食" for lk in links)


def test_get_entries_for_kanji(dictionary):
    page = dictionary.get_entries_for_kanji("食")
    assert any(e.id == 1000001 for e in page.items)


def test_get_kanji(dictionary):
    kanji = dictionary.get_kanji("食")
    assert kanji is not None
    assert kanji.literal == "食"


def test_search_kanji(dictionary):
    page = dictionary.search_kanji(query="water")
    assert any(k.literal == "水" for k in page.items)


def test_search_single_kanji(dictionary):
    result = dictionary.search("食")
    assert any(k.literal == "食" for k in result.kanji)
    assert any(e.id == 1000001 for e in result.entries.items)


def test_search_japanese_kana(dictionary):
    result = dictionary.search("みず")
    assert any(e.id == 1000002 for e in result.entries.items)
    assert any(k.literal == "水" for k in result.kanji)


def test_search_japanese_kanji_word(dictionary):
    result = dictionary.search("食べる")
    assert any(e.id == 1000001 for e in result.entries.items)
    assert any(k.literal == "食" for k in result.kanji)


def test_search_translation(dictionary):
    result = dictionary.search("water")
    assert any(e.id == 1000002 for e in result.entries.items)
    assert any(k.literal == "水" for k in result.kanji)


def test_search_translation_no_kanji_entry(dictionary):
    result = dictionary.search("thank you")
    assert any(e.id == 1000003 for e in result.entries.items)


def test_context_manager(tmp_path, conn):
    db_file = tmp_path / "test.sqlite"
    backup = sqlite3.connect(str(db_file))
    conn.backup(backup)
    backup.close()

    with patch("shodoukan.dictionary.download"):
        with Dictionary(db_path=db_file, auto_download=False) as d:
            assert d.get_kanji("水") is not None
