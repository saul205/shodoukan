import sqlite3
from unittest.mock import patch

import pytest

from shodoukan.cli import main


@pytest.fixture
def db_file(tmp_path, conn):
    path = tmp_path / "test.sqlite"
    backup = sqlite3.connect(str(path))
    conn.backup(backup)
    backup.close()
    return path


@pytest.fixture
def run(db_file, capsys):
    def _run(*args):
        with patch("shodoukan.dictionary.download"):
            main(["--db", str(db_file), *args])
        return capsys.readouterr().out

    return _run


def test_search_single_kanji(run):
    out = run("search", "食")
    assert "食" in out
    assert "食べる" in out


def test_search_kana(run):
    out = run("search", "みず")
    assert "1000002" in out
    assert "水" in out


def test_search_translation(run):
    out = run("search", "water")
    assert "1000002" in out


def test_entry(run):
    out = run("entry", "1000001")
    assert "1000001" in out
    assert "食べる" in out


def test_entry_not_found(db_file):
    with patch("shodoukan.dictionary.download"):
        with pytest.raises(SystemExit) as exc:
            main(["--db", str(db_file), "entry", "9999999"])
    assert exc.value.code == 1


def test_entry_search(run):
    out = run("entry-search", "みず")
    assert "1000002" in out


def test_entry_kanji(run):
    out = run("entry-kanji", "1000001")
    assert "食" in out


def test_entries_for_kanji(run):
    out = run("entries-for-kanji", "食")
    assert "1000001" in out


def test_kanji(run):
    out = run("kanji", "食")
    assert "食" in out
    assert "eat" in out


def test_kanji_not_found(db_file):
    with patch("shodoukan.dictionary.download"):
        with pytest.raises(SystemExit) as exc:
            main(["--db", str(db_file), "kanji", "X"])
    assert exc.value.code == 1


def test_kanji_search(run):
    out = run("kanji-search", "water")
    assert "水" in out


def test_kanji_search_no_query(run):
    out = run("kanji-search", "--grade", "1")
    assert "水" in out


def test_limit(run):
    out = run("search", "食", "--limit", "1")
    assert "of" in out
