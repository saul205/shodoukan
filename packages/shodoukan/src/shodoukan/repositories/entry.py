import os

from sqlalchemy import and_, desc, distinct, func, or_, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from shodoukan.db import schema as fts
from shodoukan.db.orm import (
    EntryKanjiORM,
    EntryORM,
    EntrySenseLangCountORM,
    ExampleORM,
    GlossORM,
    KanjiORM,
    KanjiReadingORM,
    ReadingORM,
    SenseLangIndexORM,
    SenseORM,
)
from shodoukan.models.entry import Entry, EntryKanjiLink, Page, ScoreBreakdown
from shodoukan.repositories.fts import fts_prefix_query, fts_query
from shodoukan.repositories.mapper import entry_to_domain
from shodoukan.repositories.scoring import JLPT_WEIGHT, kanji_score
from shodoukan.utils.lang import gloss_lang


def _debug_mode() -> bool:
    return os.getenv("SHODOUKAN_DEBUG") == "1"


def _load_options():
    return [
        selectinload(EntryORM.kanji_readings),
        selectinload(EntryORM.readings).selectinload(ReadingORM.restrictions),
        selectinload(EntryORM.senses).options(
            selectinload(SenseORM.glosses),
            selectinload(SenseORM.cross_references),
            selectinload(SenseORM.examples).selectinload(ExampleORM.sentences),
        ),
    ]


class EntryRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_by_id(self, entry_id: int) -> Entry | None:
        with Session(self._engine) as session:
            e = session.execute(
                select(EntryORM)
                .options(*_load_options())
                .where(EntryORM.id == entry_id)
            ).scalar_one_or_none()
        return entry_to_domain(e) if e else None

    def search_by_japanese(self, query: str, limit: int, offset: int) -> Page[Entry]:
        prefix = query + "%"
        cond = or_(
            KanjiReadingORM.kanji == query,
            KanjiReadingORM.kanji.like(prefix),
            ReadingORM.text == query,
            ReadingORM.text.like(prefix),
        )
        exact = or_(
            KanjiReadingORM.kanji == query,
            ReadingORM.text == query,
        )
        _freq_j = EntryORM.freq_score
        _jlpt_j = func.coalesce(func.max(EntryORM.jlpt), 0) * JLPT_WEIGHT
        priority = (_freq_j + _jlpt_j).label("priority")

        def base(s):
            return (
                s.select_from(EntryORM)
                .outerjoin(EntryORM.kanji_readings)
                .outerjoin(EntryORM.readings)
                .where(cond)
            )

        with Session(self._engine) as session:
            total = session.execute(
                base(select(func.count(distinct(EntryORM.id))))
            ).scalar() or 0
            debug = _debug_mode()
            cols = [EntryORM.id, func.max(exact).label("exact_match"), priority]
            if debug:
                cols += [_freq_j.label("debug_freq"), _jlpt_j.label("debug_jlpt")]
            rows = session.execute(
                base(select(*cols))
                .group_by(EntryORM.id)
                .order_by(desc("exact_match"), desc("priority"))
                .limit(limit)
                .offset(offset)
            ).all()
            entry_ids = [r.id for r in rows]
            scores = None
            if debug:
                scores = {
                    r.id: ScoreBreakdown(
                        freq=r.debug_freq,
                        jlpt_bonus=r.debug_jlpt,
                        exact_match=bool(r.exact_match),
                    )
                    for r in rows
                }
            items = self._hydrate(session, entry_ids, scores=scores)

        return Page(items=items, total=total, limit=limit, offset=offset)

    def search_by_gloss(
        self, query: str, lang: str = "en", limit: int = 20, offset: int = 0
    ) -> Page[Entry]:
        _freq = EntryORM.freq_score
        _jlpt_pts = func.coalesce(EntryORM.jlpt, 0) * JLPT_WEIGHT
        _total = EntrySenseLangCountORM.count
        _pos = func.min(SenseLangIndexORM.lang_sense_index)
        composite = (
            (_freq + _jlpt_pts)
            * (_total - _pos)
            / (_total * (0.9 + 0.1 * _total))
        ).label("composite")

        debug = _debug_mode()

        def _build(fts_q: str):
            fts_where = and_(
                text("glosses_fts MATCH :fts_q").bindparams(fts_q=fts_q),
                GlossORM.lang == gloss_lang(lang),
            )

            def base(s):
                return (
                    s.select_from(EntryORM)
                    .join(EntryORM.senses)
                    .join(SenseORM.glosses)
                    .join(fts.glosses_fts, fts.glosses_fts.c.rowid == GlossORM.id)
                    .join(
                        EntrySenseLangCountORM,
                        and_(
                            EntrySenseLangCountORM.entry_id == EntryORM.id,
                            EntrySenseLangCountORM.lang == gloss_lang(lang),
                        ),
                    )
                    .join(
                        SenseLangIndexORM,
                        and_(
                            SenseLangIndexORM.sense_id == SenseORM.id,
                            SenseLangIndexORM.lang == gloss_lang(lang),
                        ),
                    )
                    .where(fts_where)
                )

            extra = []
            if debug:
                extra = [
                    EntryORM.freq_score.label("debug_freq"),
                    _jlpt_pts.label("debug_jlpt"),
                    _pos.label("debug_sense_pos"),
                    EntrySenseLangCountORM.count.label("debug_total_senses"),
                ]

            return (
                base(
                    select(
                        EntryORM.id,
                        composite,
                        func.min(text("rank")).label("fts_rank"),
                        *extra,
                    )
                )
                .group_by(EntryORM.id)
                .order_by(text("fts_rank"), desc("composite"))
                .limit(limit)
                .offset(offset),
                base(select(func.count(distinct(EntryORM.id)))),
            )

        def _extract(rows):
            ids = [r.id for r in rows]
            if not debug:
                return ids, None
            return ids, {
                r.id: ScoreBreakdown(
                    freq=r.debug_freq,
                    jlpt_bonus=r.debug_jlpt,
                    fts_rank=r.fts_rank,
                    composite=r.composite,
                    sense_pos=r.debug_sense_pos,
                    total_senses=r.debug_total_senses,
                )
                for r in rows
            }

        with Session(self._engine) as session:
            id_stmt, count_stmt = _build(fts_query(query))
            rows = session.execute(id_stmt).all()
            entry_ids, scores = _extract(rows)
            total = session.execute(count_stmt).scalar() or 0
            if not entry_ids:
                id_stmt, count_stmt = _build(fts_prefix_query(query))
                rows = session.execute(id_stmt).all()
                entry_ids, scores = _extract(rows)
                total = session.execute(count_stmt).scalar() or 0
            items = self._hydrate(session, list(entry_ids), scores=scores)

        return Page(items=items, total=total, limit=limit, offset=offset)

    def get_kanji_literals_for_entries(self, entry_ids: list[int]) -> list[str]:
        if not entry_ids:
            return []
        with Session(self._engine) as session:
            return list(
                session.execute(
                    select(EntryKanjiORM.literal)
                    .where(EntryKanjiORM.entry_id.in_(entry_ids))
                    .distinct()
                ).scalars().all()
            )

    def get_kanji_for_entry(self, entry_id: int) -> list[EntryKanjiLink]:
        with Session(self._engine) as session:
            literals = session.execute(
                select(EntryKanjiORM.literal)
                .where(EntryKanjiORM.entry_id == entry_id)
                .order_by(EntryKanjiORM.literal)
            ).scalars().all()
        return [EntryKanjiLink(literal=lit) for lit in literals]

    def get_entries_for_kanji(
        self, literal: str, limit: int, offset: int
    ) -> Page[Entry]:
        with Session(self._engine) as session:
            total = session.execute(
                select(func.count()).where(EntryKanjiORM.literal == literal)
            ).scalar() or 0
            entry_ids = session.execute(
                select(EntryKanjiORM.entry_id)
                .join(EntryORM, EntryORM.id == EntryKanjiORM.entry_id)
                .where(EntryKanjiORM.literal == literal)
                .order_by(desc(EntryORM.freq_score))
                .limit(limit)
                .offset(offset)
            ).scalars().all()
            items = self._hydrate(session, list(entry_ids))

        return Page(items=items, total=total, limit=limit, offset=offset)

    def get_related_kanji_literals(
        self, entry_ids: list[int], limit: int = 10
    ) -> list[str]:
        if not entry_ids:
            return []
        with Session(self._engine) as session:
            rows = session.execute(
                select(
                    EntryKanjiORM.entry_id,
                    EntryKanjiORM.literal,
                    kanji_score(KanjiORM.jlpt, KanjiORM.freq).label("k_score"),
                )
                .join(KanjiORM, KanjiORM.literal == EntryKanjiORM.literal)
                .where(EntryKanjiORM.entry_id.in_(entry_ids))
            ).all()

        # Group kanji per entry, sorted by kanji score within each entry
        by_entry: dict[int, list[tuple[str, int]]] = {}
        for row in rows:
            by_entry.setdefault(row.entry_id, []).append((row.literal, row.k_score))
        for kanji_list in by_entry.values():
            kanji_list.sort(key=lambda x: x[1], reverse=True)

        # Walk entries in result order; place each kanji at its first appearance
        seen: set[str] = set()
        result: list[str] = []
        for eid in entry_ids:
            for literal, _ in by_entry.get(eid, []):
                if literal not in seen:
                    seen.add(literal)
                    result.append(literal)
                    if len(result) == limit:
                        return result
        return result

    def _hydrate(
        self,
        session: Session,
        entry_ids: list[int],
        scores: dict[int, ScoreBreakdown] | None = None,
    ) -> list[Entry]:
        if not entry_ids:
            return []
        entries = {
            e.id: e
            for e in session.execute(
                select(EntryORM)
                .options(*_load_options())
                .where(EntryORM.id.in_(entry_ids))
            ).scalars().all()
        }
        result = [entry_to_domain(entries[eid]) for eid in entry_ids if eid in entries]
        if scores:
            for entry in result:
                entry.score = scores.get(entry.id)
        return result
