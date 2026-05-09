from pathlib import Path

from shodoukan.db.connection import open_connection, resolve_path
from shodoukan.db.download import download
from shodoukan.models.entry import Entry, EntryKanjiLink, Page
from shodoukan.models.kanji import Kanji
from shodoukan.repositories.entry import EntryRepository
from shodoukan.repositories.kanji import KanjiRepository
from shodoukan.utils.detect import is_japanese


class Dictionary:
    def __init__(
        self,
        db_path: Path | str | None = None,
        auto_download: bool = True,
    ) -> None:
        self._path = resolve_path(db_path)
        if auto_download:
            download(self._path)
        self._conn = open_connection(self._path)
        self._entries = EntryRepository(self._conn)
        self._kanji = KanjiRepository(self._conn)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Dictionary":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # --- Entries ---

    def get_entry(self, entry_id: int) -> Entry | None:
        return self._entries.get_by_id(entry_id)

    def search_entries(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Page[Entry]:
        if is_japanese(query):
            return self._entries.search_by_japanese(query, limit=limit, offset=offset)
        return self._entries.search_by_english(query, limit=limit, offset=offset)

    def get_kanji_for_entry(self, entry_id: int) -> list[EntryKanjiLink]:
        return self._entries.get_kanji_for_entry(entry_id)

    def get_entries_for_kanji(
        self,
        literal: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Page[Entry]:
        return self._entries.get_entries_for_kanji(literal, limit=limit, offset=offset)

    # --- Kanji ---

    def get_kanji(self, literal: str) -> Kanji | None:
        return self._kanji.get_by_literal(literal)

    def search_kanji(
        self,
        query: str | None = None,
        grade: int | None = None,
        jlpt: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Page[Kanji]:
        return self._kanji.search(query=query, grade=grade, jlpt=jlpt, limit=limit, offset=offset)

    @staticmethod
    def download_db(dest: Path | str | None = None, force: bool = False) -> None:
        download(resolve_path(dest), force=force)
