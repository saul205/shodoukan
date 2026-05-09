import json
import sqlite3
from collections import defaultdict

from shodoukan.models.entry import Page
from shodoukan.models.kanji import Kanji, KanjiMeaning
from shodoukan.utils.detect import contains_kanji, contains_kana


def _json(value: str) -> list[str]:
    return json.loads(value) if value else []


def _fts_query(text: str) -> str:
    escaped = text.replace('"', '""')
    return f'"{escaped}"'


def _fts_prefix_query(text: str) -> str:
    return " ".join(f"{word}*" for word in text.split())


class KanjiRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_by_literal(self, literal: str) -> Kanji | None:
        row = self._conn.execute(
            "SELECT literal, grade, stroke_count, freq, jlpt, on_readings, kun_readings, nanori FROM kanji WHERE literal = ?",
            (literal,),
        ).fetchone()
        if row is None:
            return None
        meanings = self._fetch_meanings([literal])
        return self._build(row, meanings[literal])

    def search(
        self,
        query: str | None,
        grade: int | None,
        jlpt: int | None,
        limit: int,
        offset: int,
    ) -> Page[Kanji]:
        if query and len(query) == 1 and contains_kanji(query):
            k = self.get_by_literal(query)
            if k is None:
                return Page(items=[], total=0, limit=limit, offset=offset)
            # Apply grade/jlpt filters
            if grade is not None and k.grade != grade:
                return Page(items=[], total=0, limit=limit, offset=offset)
            if jlpt is not None and k.jlpt != jlpt:
                return Page(items=[], total=0, limit=limit, offset=offset)
            return Page(items=[k], total=1, limit=limit, offset=offset)

        if query and contains_kana(query):
            return self._search_by_reading(query, grade, jlpt, limit, offset)

        return self._search_by_meaning(query, grade, jlpt, limit, offset)

    def _grade_jlpt_clauses(self, grade: int | None, jlpt: int | None) -> tuple[str, list]:
        clauses, params = [], []
        if grade is not None:
            clauses.append("k.grade = ?")
            params.append(grade)
        if jlpt is not None:
            clauses.append("k.jlpt = ?")
            params.append(jlpt)
        sql = (" AND " + " AND ".join(clauses)) if clauses else ""
        return sql, params

    def _search_by_reading(
        self, query: str, grade: int | None, jlpt: int | None, limit: int, offset: int
    ) -> Page[Kanji]:
        extra_sql, extra_params = self._grade_jlpt_clauses(grade, jlpt)
        base = f"""
            FROM kanji k
            WHERE (
                EXISTS (SELECT 1 FROM json_each(k.on_readings) WHERE value = ?)
                OR EXISTS (SELECT 1 FROM json_each(k.kun_readings) WHERE value = ?)
                OR EXISTS (SELECT 1 FROM json_each(k.on_readings) WHERE value LIKE ? || '%')
                OR EXISTS (SELECT 1 FROM json_each(k.kun_readings) WHERE value LIKE ? || '.' || '%')
            ){extra_sql}
        """
        base_params = [query, query, query, query] + extra_params

        total = self._conn.execute(f"SELECT COUNT(*) {base}", base_params).fetchone()[0]
        rows = self._conn.execute(
            f"SELECT k.literal, k.grade, k.stroke_count, k.freq, k.jlpt, k.on_readings, k.kun_readings, k.nanori {base} LIMIT ? OFFSET ?",
            base_params + [limit, offset],
        ).fetchall()

        return self._build_page(rows, total, limit, offset)

    def _search_by_meaning(
        self, query: str | None, grade: int | None, jlpt: int | None, limit: int, offset: int
    ) -> Page[Kanji]:
        extra_sql, extra_params = self._grade_jlpt_clauses(grade, jlpt)

        if query:
            def _run(fts_q: str) -> tuple[list, int]:
                rows = self._conn.execute(
                    f"""
                    SELECT DISTINCT k.literal, k.grade, k.stroke_count, k.freq, k.jlpt,
                        k.on_readings, k.kun_readings, k.nanori
                    FROM kanji k
                    JOIN kanji_meanings km ON km.literal = k.literal
                    JOIN kanji_meanings_fts kmf ON kmf.rowid = km.id
                    WHERE kanji_meanings_fts MATCH ? AND km.lang = 'en'{extra_sql}
                    ORDER BY rank
                    LIMIT ? OFFSET ?
                    """,
                    [fts_q] + extra_params + [limit, offset],
                ).fetchall()
                total_row = self._conn.execute(
                    f"""
                    SELECT COUNT(DISTINCT k.literal)
                    FROM kanji k
                    JOIN kanji_meanings km ON km.literal = k.literal
                    JOIN kanji_meanings_fts kmf ON kmf.rowid = km.id
                    WHERE kanji_meanings_fts MATCH ? AND km.lang = 'en'{extra_sql}
                    """,
                    [fts_q] + extra_params,
                ).fetchone()
                return rows, (total_row[0] if total_row else 0)

            rows, total = _run(_fts_query(query))
            if not rows:
                rows, total = _run(_fts_prefix_query(query))
        else:
            base = f"FROM kanji k WHERE 1=1{extra_sql}"
            total = self._conn.execute(f"SELECT COUNT(*) {base}", extra_params).fetchone()[0]
            rows = self._conn.execute(
                f"SELECT k.literal, k.grade, k.stroke_count, k.freq, k.jlpt, k.on_readings, k.kun_readings, k.nanori {base} LIMIT ? OFFSET ?",
                extra_params + [limit, offset],
            ).fetchall()

        return self._build_page(rows, total, limit, offset)

    def _fetch_meanings(self, literals: list[str]) -> dict[str, list[KanjiMeaning]]:
        if not literals:
            return {}
        ph = ",".join("?" * len(literals))
        rows = self._conn.execute(
            f"SELECT literal, text, lang FROM kanji_meanings WHERE literal IN ({ph})",
            literals,
        ).fetchall()
        result: dict[str, list[KanjiMeaning]] = defaultdict(list)
        for r in rows:
            result[r["literal"]].append(KanjiMeaning(text=r["text"], lang=r["lang"]))
        return result

    def _build(self, row: sqlite3.Row, meanings: list[KanjiMeaning]) -> Kanji:
        return Kanji(
            literal=row["literal"],
            grade=row["grade"],
            stroke_count=row["stroke_count"],
            freq=row["freq"],
            jlpt=row["jlpt"],
            on_readings=_json(row["on_readings"]),
            kun_readings=_json(row["kun_readings"]),
            nanori=_json(row["nanori"]),
            meanings=meanings,
        )

    def _build_page(self, rows: list[sqlite3.Row], total: int, limit: int, offset: int) -> Page[Kanji]:
        literals = [r["literal"] for r in rows]
        meanings = self._fetch_meanings(literals)
        items = [self._build(r, meanings[r["literal"]]) for r in rows]
        return Page(items=items, total=total, limit=limit, offset=offset)
