import json
import sqlite3
from collections import defaultdict

from shodoukan.models.entry import (
    CrossReference,
    Entry,
    EntryKanjiLink,
    Example,
    ExampleSentence,
    Gloss,
    KanjiReading,
    Page,
    Reading,
    Sense,
)


def _json(value: str) -> list[str]:
    return json.loads(value) if value else []


def _fts_query(text: str) -> str:
    escaped = text.replace('"', '""')
    return f'"{escaped}"'


def _fts_prefix_query(text: str) -> str:
    return " ".join(f"{word}*" for word in text.split())


class EntryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_by_id(self, entry_id: int) -> Entry | None:
        row = self._conn.execute(
            "SELECT id FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if row is None:
            return None
        entries = self._hydrate([entry_id])
        return entries[0] if entries else None

    def search_by_japanese(self, query: str, limit: int, offset: int) -> Page[Entry]:
        prefix = query + "%"
        count_row = self._conn.execute(
            """
            SELECT COUNT(DISTINCT e.id)
            FROM entries e
            LEFT JOIN kanji_readings kr ON kr.entry_id = e.id
            LEFT JOIN readings r ON r.entry_id = e.id
            WHERE kr.kanji = ? OR r.text = ? OR r.text LIKE ?
            """,
            (query, query, prefix),
        ).fetchone()
        total = count_row[0] if count_row else 0

        rows = self._conn.execute(
            """
            SELECT DISTINCT e.id,
                (kr.kanji = ? OR r.text = ?) AS exact_match
            FROM entries e
            LEFT JOIN kanji_readings kr ON kr.entry_id = e.id
            LEFT JOIN readings r ON r.entry_id = e.id
            WHERE kr.kanji = ? OR r.text = ? OR r.text LIKE ?
            ORDER BY exact_match DESC
            LIMIT ? OFFSET ?
            """,
            (query, query, query, query, prefix, limit, offset),
        ).fetchall()

        entry_ids = [r["id"] for r in rows]
        return Page(items=self._hydrate(entry_ids), total=total, limit=limit, offset=offset)

    def search_by_english(self, query: str, limit: int, offset: int) -> Page[Entry]:
        def _run(fts_q: str) -> list[sqlite3.Row]:
            return self._conn.execute(
                """
                SELECT DISTINCT e.id
                FROM entries e
                JOIN senses s ON s.entry_id = e.id
                JOIN glosses g ON g.sense_id = s.id
                JOIN glosses_fts gf ON gf.rowid = g.id
                WHERE glosses_fts MATCH ? AND g.lang = 'eng'
                ORDER BY rank
                LIMIT ? OFFSET ?
                """,
                (fts_q, limit, offset),
            ).fetchall()

        def _count(fts_q: str) -> int:
            row = self._conn.execute(
                """
                SELECT COUNT(DISTINCT e.id)
                FROM entries e
                JOIN senses s ON s.entry_id = e.id
                JOIN glosses g ON g.sense_id = s.id
                JOIN glosses_fts gf ON gf.rowid = g.id
                WHERE glosses_fts MATCH ? AND g.lang = 'eng'
                """,
                (fts_q,),
            ).fetchone()
            return row[0] if row else 0

        rows = _run(_fts_query(query))
        total = _count(_fts_query(query))
        if not rows:
            fallback = _fts_prefix_query(query)
            rows = _run(fallback)
            total = _count(fallback)

        entry_ids = [r["id"] for r in rows]
        return Page(items=self._hydrate(entry_ids), total=total, limit=limit, offset=offset)

    def get_kanji_for_entry(self, entry_id: int) -> list[EntryKanjiLink]:
        rows = self._conn.execute(
            """
            SELECT literal, priority_score
            FROM entry_kanji
            WHERE entry_id = ?
            ORDER BY priority_score DESC
            """,
            (entry_id,),
        ).fetchall()
        return [EntryKanjiLink(literal=r["literal"], priority_score=r["priority_score"]) for r in rows]

    def get_entries_for_kanji(self, literal: str, limit: int, offset: int) -> Page[Entry]:
        count_row = self._conn.execute(
            "SELECT COUNT(*) FROM entry_kanji WHERE literal = ?", (literal,)
        ).fetchone()
        total = count_row[0] if count_row else 0

        rows = self._conn.execute(
            """
            SELECT entry_id FROM entry_kanji
            WHERE literal = ?
            ORDER BY priority_score DESC
            LIMIT ? OFFSET ?
            """,
            (literal, limit, offset),
        ).fetchall()

        entry_ids = [r["entry_id"] for r in rows]
        return Page(items=self._hydrate(entry_ids), total=total, limit=limit, offset=offset)

    def get_related_kanji_literals(self, entry_ids: list[int], limit: int = 10) -> list[str]:
        if not entry_ids:
            return []
        ph = ",".join("?" * len(entry_ids))
        rows = self._conn.execute(
            f"""
            SELECT ek.literal, MAX(ek.priority_score) AS score
            FROM entry_kanji ek
            WHERE ek.entry_id IN ({ph})
            GROUP BY ek.literal
            ORDER BY score DESC
            LIMIT ?
            """,
            [*entry_ids, limit],
        ).fetchall()
        return [r["literal"] for r in rows]

    def _hydrate(self, entry_ids: list[int]) -> list[Entry]:
        if not entry_ids:
            return []

        ph = ",".join("?" * len(entry_ids))

        kr_rows = self._conn.execute(
            f"SELECT id, entry_id, kanji, priority, info FROM kanji_readings WHERE entry_id IN ({ph})",
            entry_ids,
        ).fetchall()

        r_rows = self._conn.execute(
            f"SELECT id, entry_id, text, no_kanji, priority, info FROM readings WHERE entry_id IN ({ph})",
            entry_ids,
        ).fetchall()

        # Map reading_id → list of kanji literals it's restricted to
        kr_by_id = {row["id"]: row["kanji"] for row in kr_rows}
        rr_rows = self._conn.execute(
            f"""
            SELECT rr.reading_id, kr.kanji
            FROM reading_restrictions rr
            JOIN kanji_readings kr ON rr.kanji_reading_id = kr.id
            WHERE kr.entry_id IN ({ph})
            """,
            entry_ids,
        ).fetchall()
        restrictions: dict[int, list[str]] = defaultdict(list)
        for rr in rr_rows:
            restrictions[rr["reading_id"]].append(rr["kanji"])

        sense_rows = self._conn.execute(
            f"SELECT id, entry_id, pos, misc, dialects, info FROM senses WHERE entry_id IN ({ph})",
            entry_ids,
        ).fetchall()
        sense_ids = [s["id"] for s in sense_rows]

        glosses: dict[int, list[Gloss]] = defaultdict(list)
        xrefs: dict[int, list[CrossReference]] = defaultdict(list)
        examples: dict[int, list[Example]] = defaultdict(list)

        if sense_ids:
            sph = ",".join("?" * len(sense_ids))

            for g in self._conn.execute(
                f"SELECT id, sense_id, text, type, lang FROM glosses WHERE sense_id IN ({sph})",
                sense_ids,
            ).fetchall():
                glosses[g["sense_id"]].append(
                    Gloss(id=g["id"], text=g["text"], type=g["type"], lang=g["lang"])
                )

            for x in self._conn.execute(
                f"SELECT sense_id, reference, reading, sense_idx FROM cross_references WHERE sense_id IN ({sph})",
                sense_ids,
            ).fetchall():
                xrefs[x["sense_id"]].append(
                    CrossReference(
                        reference=x["reference"],
                        reading=x["reading"],
                        sense_idx=x["sense_idx"],
                    )
                )

            ex_rows = self._conn.execute(
                f"SELECT id, sense_id, source_name, source_id, text FROM examples WHERE sense_id IN ({sph})",
                sense_ids,
            ).fetchall()
            ex_ids = [e["id"] for e in ex_rows]

            sentences: dict[int, list[ExampleSentence]] = defaultdict(list)
            if ex_ids:
                eph = ",".join("?" * len(ex_ids))
                for s in self._conn.execute(
                    f"SELECT example_id, lang, text FROM example_sentences WHERE example_id IN ({eph})",
                    ex_ids,
                ).fetchall():
                    sentences[s["example_id"]].append(
                        ExampleSentence(lang=s["lang"], text=s["text"])
                    )

            for e in ex_rows:
                examples[e["sense_id"]].append(
                    Example(
                        id=e["id"],
                        source_name=e["source_name"],
                        source_id=e["source_id"],
                        text=e["text"],
                        sentences=sentences[e["id"]],
                    )
                )

        # Group by entry_id
        kr_by_entry: dict[int, list[KanjiReading]] = defaultdict(list)
        for row in kr_rows:
            kr_by_entry[row["entry_id"]].append(
                KanjiReading(
                    id=row["id"],
                    kanji=row["kanji"],
                    priority=_json(row["priority"]),
                    info=_json(row["info"]),
                )
            )

        r_by_entry: dict[int, list[Reading]] = defaultdict(list)
        for row in r_rows:
            r_by_entry[row["entry_id"]].append(
                Reading(
                    id=row["id"],
                    text=row["text"],
                    no_kanji=bool(row["no_kanji"]),
                    priority=_json(row["priority"]),
                    info=_json(row["info"]),
                    restricted_to=restrictions[row["id"]],
                )
            )

        s_by_entry: dict[int, list[Sense]] = defaultdict(list)
        for row in sense_rows:
            s_by_entry[row["entry_id"]].append(
                Sense(
                    id=row["id"],
                    pos=_json(row["pos"]),
                    misc=_json(row["misc"]),
                    dialects=_json(row["dialects"]),
                    info=_json(row["info"]),
                    glosses=glosses[row["id"]],
                    cross_references=xrefs[row["id"]],
                    examples=examples[row["id"]],
                )
            )

        order = {eid: i for i, eid in enumerate(entry_ids)}
        result = [
            Entry(
                id=eid,
                kanji_readings=kr_by_entry[eid],
                readings=r_by_entry[eid],
                senses=s_by_entry[eid],
            )
            for eid in entry_ids
        ]
        return sorted(result, key=lambda e: order[e.id])
