from pathlib import Path

from shodoukan.db.connection import open_connection, resolve_path
from shodoukan.db.download import download
from shodoukan.models.entry import Entry, EntryKanjiLink, Page
from shodoukan.models.kanji import Kanji
from shodoukan.models.search import SearchResult
from shodoukan.repositories.entry import EntryRepository
from shodoukan.repositories.kanji import KanjiRepository
from shodoukan.utils.detect import contains_kanji, is_japanese, is_romaji
from shodoukan.utils.romaji import to_hiragana


class Dictionary:
    def __init__(
        self,
        db_path: Path | str | None = None,
        auto_download: bool = True,
    ) -> None:
        self._path = resolve_path(db_path)
        if auto_download:
            download(self._path)
        self._engine = open_connection(self._path)
        self._entries = EntryRepository(self._engine)
        self._kanji = KanjiRepository(self._engine)

    def close(self) -> None:
        self._engine.dispose()

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
        lang: str = "en",
        limit: int = 20,
        offset: int = 0,
    ) -> Page[Entry]:
        if is_japanese(query):
            return self._entries.search_by_japanese(query, limit=limit, offset=offset)
        if is_romaji(query):
            hiragana = to_hiragana(query)
            if hiragana:
                return self._entries.search_by_japanese(hiragana, limit=limit, offset=offset)
        return self._entries.search_by_gloss(
            query, lang=lang, limit=limit, offset=offset
        )

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
        lang: str = "en",
        limit: int = 20,
        offset: int = 0,
    ) -> Page[Kanji]:
        return self._kanji.search(
            query=query, grade=grade, jlpt=jlpt, lang=lang, limit=limit, offset=offset
        )

    def search(
        self,
        query: str,
        lang: str = "en",
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResult:
        if len(query) == 1 and contains_kanji(query):
            return self._search_single_kanji(query, limit, offset)
        if is_japanese(query):
            return self._search_japanese(query, limit, offset)
        if is_romaji(query):
            hiragana = to_hiragana(query)
            if hiragana:
                return self._search_japanese(hiragana, limit, offset)
        return self._search_translation(query, lang=lang, limit=limit, offset=offset)

    def _search_single_kanji(
        self, literal: str, limit: int, offset: int
    ) -> SearchResult:
        kanji = self._kanji.get_by_literal(literal)
        entries = self._entries.get_entries_for_kanji(
            literal, limit=limit, offset=offset
        )
        return SearchResult(entries=entries, kanji=[kanji] if kanji else [])

    def _search_japanese(self, query: str, limit: int, offset: int) -> SearchResult:
        entries = self._entries.search_by_japanese(query, limit=limit, offset=offset)
        entry_ids = [e.id for e in entries.items]
        literals = self._entries.get_related_kanji_literals(entry_ids, limit=10)
        kanji = [k for lit in literals if (k := self._kanji.get_by_literal(lit))]
        return SearchResult(entries=entries, kanji=kanji)

    def _search_translation(
        self, query: str, lang: str, limit: int, offset: int
    ) -> SearchResult:
        entries = self._entries.search_by_gloss(
            query, lang=lang, limit=limit, offset=offset
        )
        entry_ids = [e.id for e in entries.items]

        related_literals = self._entries.get_related_kanji_literals(entry_ids, limit=10)
        meaning_page = self._kanji.search(
            query=query, grade=None, jlpt=None, lang=lang, limit=5, offset=0
        )
        meaning_literals = [k.literal for k in meaning_page.items]

        seen: set[str] = set()
        merged: list[str] = []
        for lit in related_literals + meaning_literals:
            if lit not in seen:
                seen.add(lit)
                merged.append(lit)

        kanji = [k for lit in merged[:10] if (k := self._kanji.get_by_literal(lit))]
        return SearchResult(entries=entries, kanji=kanji)

    @staticmethod
    def download_db(dest: Path | str | None = None, force: bool = False) -> None:
        download(resolve_path(dest), force=force)
