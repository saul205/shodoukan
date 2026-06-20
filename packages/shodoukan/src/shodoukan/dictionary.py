from pathlib import Path

from shodoukan.db.connection import open_connection, resolve_path
from shodoukan.db.download import download
from shodoukan.models.entry import Entry, EntryKanjiLink, Page
from shodoukan.models.kanji import Kanji
from shodoukan.models.search import SearchResult
from shodoukan.repositories.entry import EntryRepository
from shodoukan.repositories.kanji import KanjiRepository
from shodoukan.repositories.scoring import kanji_score_value
from shodoukan.utils.detect import is_japanese, is_kanji_only, is_romaji
from shodoukan.utils.romaji import to_hiragana

_KANJI_SIDE_LIMIT = 10


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
        if is_kanji_only(query):
            return self._search_literals(query, limit, offset)
        if is_japanese(query):
            return self._search_japanese(query, limit, offset)
        if is_romaji(query):
            hiragana = to_hiragana(query)
            if hiragana:
                return self._search_japanese(hiragana, limit, offset)
        return self._search_translation(query, lang=lang, limit=limit, offset=offset)

    def _search_literals(self, query: str, limit: int, offset: int) -> SearchResult:
        entries = self._entries.search_by_japanese(query, limit=limit, offset=offset)
        seen: dict[str, Kanji] = {}
        for ch in query:
            if ch not in seen:
                k = self._kanji.get_by_literal(ch)
                if k:
                    seen[ch] = k
        kanji = sorted(seen.values(), key=kanji_score_value, reverse=True)
        return SearchResult(entries=entries, kanji=kanji)

    def _search_japanese(self, query: str, limit: int, offset: int) -> SearchResult:
        entries = self._entries.search_by_japanese(query, limit=limit, offset=offset)
        entry_ids = [e.id for e in entries.items]
        literals_a = self._entries.get_kanji_literals_for_entries(entry_ids)
        kanji_b = self._kanji.search(
            query=query, grade=None, jlpt=None, limit=_KANJI_SIDE_LIMIT, offset=0,
        ).items
        return SearchResult(
            entries=entries, kanji=self._merge_kanji(literals_a, kanji_b)
        )

    def _search_translation(
        self, query: str, lang: str, limit: int, offset: int
    ) -> SearchResult:
        entries = self._entries.search_by_gloss(
            query, lang=lang, limit=limit, offset=offset
        )
        entry_ids = [e.id for e in entries.items]
        literals_a = self._entries.get_kanji_literals_for_entries(entry_ids)
        kanji_b = self._kanji.search(
            query=query, grade=None, jlpt=None, lang=lang,
            limit=_KANJI_SIDE_LIMIT, offset=0,
        ).items
        return SearchResult(
            entries=entries, kanji=self._merge_kanji(literals_a, kanji_b)
        )

    def _merge_kanji(
        self, literals_a: list[str], kanji_b: list[Kanji]
    ) -> list[Kanji]:
        kanji_a = self._kanji.get_by_literals(literals_a)
        seen: dict[str, Kanji] = {}
        for k in (*kanji_a, *kanji_b):
            seen.setdefault(k.literal, k)
        return sorted(
            seen.values(), key=kanji_score_value, reverse=True
        )[:_KANJI_SIDE_LIMIT]

    def get_kanji_for_entry_related(self, entry_id: int) -> list[Kanji]:
        literals = self._entries.get_related_kanji_literals([entry_id])
        return [k for lit in literals if (k := self._kanji.get_by_literal(lit))]

    @staticmethod
    def download_db(dest: Path | str | None = None, force: bool = False) -> None:
        download(resolve_path(dest), force=force)
