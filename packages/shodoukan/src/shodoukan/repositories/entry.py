import os

from sqlalchemy import (
    and_,
    case,
    desc,
    func,
    null,
    or_,
    select,
    text,
    union_all,
)
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
from shodoukan.repositories.scoring import (
    GLOSS_TIER_2_RELEVANCE,
    GLOSS_TIER_3_RELEVANCE,
    JLPT_WEIGHT,
    TIER_READING_EXACT,
    TIER_READING_PREFIX,
    TIER_WEIGHT,
    kanji_score,
)
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


# Per-match details carried through the union for debug mode.
_DETAIL_COLUMNS = (
    "match_tier",
    "fts_rank",
    "relevance",
    "freq",
    "jlpt_bonus",
    "exact_match",
    "composite",
    "sense_pos",
    "total_senses",
)


def _gloss_join(stmt, fts_q: str, lang: str):
    """`stmt` over entries with a gloss in `lang` matching the FTS query."""
    code = gloss_lang(lang)
    return (
        stmt.select_from(EntryORM)
        .join(EntryORM.senses)
        .join(SenseORM.glosses)
        .join(fts.glosses_fts, fts.glosses_fts.c.rowid == GlossORM.id)
        .join(
            EntrySenseLangCountORM,
            and_(
                EntrySenseLangCountORM.entry_id == EntryORM.id,
                EntrySenseLangCountORM.lang == code,
            ),
        )
        .join(
            SenseLangIndexORM,
            and_(
                SenseLangIndexORM.sense_id == SenseORM.id,
                SenseLangIndexORM.lang == code,
            ),
        )
        .where(
            text("glosses_fts MATCH :fts_q").bindparams(fts_q=fts_q),
            GlossORM.lang == code,
        )
    )


def _breakdown(row) -> ScoreBreakdown:
    return ScoreBreakdown(
        score=row.score,
        match_tier=row.match_tier,
        relevance=row.relevance,
        freq=row.freq,
        jlpt_bonus=row.jlpt_bonus,
        exact_match=None if row.exact_match is None else bool(row.exact_match),
        fts_rank=row.fts_rank,
        composite=row.composite,
        sense_pos=row.sense_pos,
        total_senses=row.total_senses,
    )


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
        """Entries whose spelling or reading equals or starts with `query`."""
        return self.search(reading_query=query, limit=limit, offset=offset)

    def search_by_gloss(
        self, query: str, lang: str = "en", limit: int = 20, offset: int = 0
    ) -> Page[Entry]:
        """Entries with a gloss in `lang` matching `query` (FTS)."""
        return self.search(gloss_query=query, lang=lang, limit=limit, offset=offset)

    def search(
        self,
        reading_query: str | None = None,
        gloss_query: str | None = None,
        lang: str = "en",
        limit: int = 20,
        offset: int = 0,
    ) -> Page[Entry]:
        """One ranked search over reading matches, gloss matches, or both.

        Every match gets `score = match_tier * TIER_WEIGHT + popularity` (see
        `scoring.py`), so reading and gloss matches share one order. An entry
        found both ways counts once, with its best score. Ordering, pagination
        and the total are done in SQL over all matches.
        """
        branches = []
        if reading_query:
            branches.append(self._reading_matches(reading_query))
        if gloss_query:
            branches.append(self._gloss_matches(gloss_query, lang))
        if not branches:
            return Page(items=[], total=0, limit=limit, offset=offset)

        hits = union_all(*branches).subquery("hits")
        # SQLite: bare columns next to MAX() come from the row with the max, so
        # an entry matched both ways keeps the details of its best match.
        best = (
            select(
                hits.c.id,
                func.max(hits.c.score).label("score"),
                *[hits.c[name] for name in _DETAIL_COLUMNS],
            )
            .group_by(hits.c.id)
            .subquery("best")
        )
        page_stmt = (
            select(best, func.count().over().label("total"))
            .order_by(
                desc(best.c.score), best.c.fts_rank.asc().nulls_first(), best.c.id
            )
            .limit(limit)
            .offset(offset)
        )

        with Session(self._engine) as session:
            rows = session.execute(page_stmt).all()
            if rows:
                total = rows[0].total
            else:
                total = session.execute(select(func.count()).select_from(best)).scalar()
            scores = {r.id: _breakdown(r) for r in rows} if _debug_mode() else None
            items = self._hydrate(session, [r.id for r in rows], scores=scores)

        return Page(items=items, total=total or 0, limit=limit, offset=offset)

    def _reading_matches(self, query: str):
        """Entries whose spelling or reading equals (tier 3) or starts with (2)."""
        prefix = query + "%"
        cond = or_(
            KanjiReadingORM.kanji == query,
            KanjiReadingORM.kanji.like(prefix),
            ReadingORM.text == query,
            ReadingORM.text.like(prefix),
        )
        exact = func.max(or_(KanjiReadingORM.kanji == query, ReadingORM.text == query))
        jlpt_bonus = func.coalesce(func.max(EntryORM.jlpt), 0) * JLPT_WEIGHT
        popularity = EntryORM.freq_score + jlpt_bonus
        tier = case((exact == 1, TIER_READING_EXACT), else_=TIER_READING_PREFIX)
        return (
            select(
                EntryORM.id.label("id"),
                (tier * TIER_WEIGHT + popularity).label("score"),
                tier.label("match_tier"),
                null().label("fts_rank"),
                null().label("relevance"),
                EntryORM.freq_score.label("freq"),
                jlpt_bonus.label("jlpt_bonus"),
                exact.label("exact_match"),
                null().label("composite"),
                null().label("sense_pos"),
                null().label("total_senses"),
            )
            .select_from(EntryORM)
            .outerjoin(EntryORM.kanji_readings)
            .outerjoin(EntryORM.readings)
            .where(cond)
            .group_by(EntryORM.id)
        )

    def _gloss_matches(self, query: str, lang: str):
        """Entries with a matching gloss; tier from bm25 relative to the best.

        Tries the phrase first and falls back to a prefix match when the
        phrase matches nothing.
        """
        fts_q = fts_query(query)
        if not self._gloss_phrase_exists(fts_q, lang):
            fts_q = fts_prefix_query(query)

        jlpt_bonus = func.coalesce(EntryORM.jlpt, 0) * JLPT_WEIGHT
        total_senses = EntrySenseLangCountORM.count
        sense_pos = func.min(SenseLangIndexORM.lang_sense_index)
        # Decay by the matched sense's position only (see scoring.py).
        composite = (EntryORM.freq_score + jlpt_bonus) / func.log2(sense_pos + 2)
        per_entry = (
            _gloss_join(
                select(
                    EntryORM.id.label("id"),
                    composite.label("composite"),
                    func.min(text("rank")).label("fts_rank"),
                    EntryORM.freq_score.label("freq"),
                    jlpt_bonus.label("jlpt_bonus"),
                    sense_pos.label("sense_pos"),
                    total_senses.label("total_senses"),
                ),
                fts_q,
                lang,
            )
            .group_by(EntryORM.id)
            .subquery("gloss_per_entry")
        )
        ranked = select(
            per_entry,
            func.min(per_entry.c.fts_rank).over().label("best_rank"),
        ).subquery("gloss_ranked")
        # bm25 ranks are negative (lower is better) and best_rank is the lowest:
        # rank / best_rank is 1 for the best match and smaller for weaker ones.
        relevance = func.coalesce(ranked.c.fts_rank / ranked.c.best_rank, 1.0)
        tier = case(
            (relevance >= GLOSS_TIER_3_RELEVANCE, 3),
            (relevance >= GLOSS_TIER_2_RELEVANCE, 2),
            else_=1,
        )
        return select(
            ranked.c.id,
            (tier * TIER_WEIGHT + ranked.c.composite).label("score"),
            tier.label("match_tier"),
            ranked.c.fts_rank,
            relevance.label("relevance"),
            ranked.c.freq,
            ranked.c.jlpt_bonus,
            null().label("exact_match"),
            ranked.c.composite,
            ranked.c.sense_pos,
            ranked.c.total_senses,
        )

    def _gloss_phrase_exists(self, fts_q: str, lang: str) -> bool:
        # Start from the FTS match (materialized): joined with LIMIT 1, SQLite
        # would scan every gloss of the language and probe FTS for each.
        hits = (
            select(fts.glosses_fts.c.rowid.label("gloss_id"))
            .where(text("glosses_fts MATCH :fts_q").bindparams(fts_q=fts_q))
            .cte("fts_hits")
            .prefix_with("MATERIALIZED")
        )
        stmt = (
            select(GlossORM.id)
            .join(hits, hits.c.gloss_id == GlossORM.id)
            .where(GlossORM.lang == gloss_lang(lang))
            .limit(1)
        )
        with Session(self._engine) as session:
            return session.execute(stmt).first() is not None

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
