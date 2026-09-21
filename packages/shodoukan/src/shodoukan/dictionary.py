from pathlib import Path

from shodoukan.db.connection import open_connection, resolve_path
from shodoukan.db.download import download
from shodoukan.models.entry import Entry, EntryKanjiLink, Page
from shodoukan.models.kanji import Kanji
from shodoukan.models.search import SearchResult
from shodoukan.repositories.entry import EntryRepository
from shodoukan.repositories.kanji import KanjiRepository
from shodoukan.repositories.scoring import kanji_score_value
from shodoukan.utils.detect import contains_kanji, is_japanese, is_kanji_only, is_romaji
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
                jp_page = self._entries.search_by_japanese(
                    hiragana, limit=limit, offset=offset
                )
                gloss_page = self._entries.search_by_gloss(
                    query, lang=lang, limit=limit, offset=offset
                )
                seen = {e.id for e in jp_page.items}
                merged = jp_page.items + [e for e in gloss_page.items if e.id not in seen]
                return Page(
                    items=merged[:limit],
                    total=gloss_page.total,
                    limit=limit,
                    offset=offset,
                )
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
            entries = self._entries.search_by_japanese(
                query, limit=limit, offset=offset
            )
            kanji = self._literal_kanji(query)
        elif is_japanese(query):
            entries = self._entries.search_by_japanese(
                query, limit=limit, offset=offset
            )
            kanji = self._kanji.search(
                query, grade=None, jlpt=None, limit=_KANJI_SIDE_LIMIT, offset=0
            ).items
        elif is_romaji(query) and (hiragana := to_hiragana(query)):
            jp_page = self._entries.search_by_japanese(
                hiragana, limit=limit, offset=offset
            )
            gloss_page = self._entries.search_by_gloss(
                query, lang=lang, limit=limit, offset=offset
            )
            seen = {e.id for e in jp_page.items}
            merged = jp_page.items + [e for e in gloss_page.items if e.id not in seen]
            merged.sort(key=lambda e: (not e.is_common, -(e.jlpt or 0)))
            entries = Page(
                items=merged[:limit], total=gloss_page.total, limit=limit, offset=offset
            )
            jp_kanji = self._kanji.search(
                hiragana, grade=None, jlpt=None, limit=_KANJI_SIDE_LIMIT, offset=0
            ).items
            gloss_kanji = self._kanji.search(
                query, grade=None, jlpt=None, lang=lang,
                limit=_KANJI_SIDE_LIMIT, offset=0,
            ).items
            seen_lit = {k.literal for k in jp_kanji}
            kanji = sorted(
                jp_kanji + [k for k in gloss_kanji if k.literal not in seen_lit],
                key=kanji_score_value,
                reverse=True,
            )[:_KANJI_SIDE_LIMIT]
        else:
            entries = self._entries.search_by_gloss(
                query, lang=lang, limit=limit, offset=offset
            )
            kanji = self._kanji.search(
                query, grade=None, jlpt=None, lang=lang,
                limit=_KANJI_SIDE_LIMIT, offset=0,
            ).items
        return SearchResult(entries=entries, kanji=kanji)

    def _literal_kanji(self, query: str) -> list[Kanji]:
        literals = list(dict.fromkeys(ch for ch in query if contains_kanji(ch)))
        if not literals:
            return []
        return sorted(
            self._kanji.get_by_literals(literals), key=kanji_score_value, reverse=True
        )

    def get_kanji_for_entry_related(self, entry_id: int) -> list[Kanji]:
        literals = self._entries.get_related_kanji_literals([entry_id])
        return [k for lit in literals if (k := self._kanji.get_by_literal(lit))]

    @staticmethod
    def download_db(dest: Path | str | None = None, force: bool = False) -> None:
        download(resolve_path(dest), force=force)
