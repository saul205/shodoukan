import unicodedata

from sqlalchemy import and_, case, desc, func, select, text, true, union_all
from sqlalchemy import literal as sql_literal
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from shodoukan.db import schema as fts
from shodoukan.db.orm import KanjiMeaningORM, KanjiORM, KanjiSvgORM
from shodoukan.models.entry import Page
from shodoukan.models.kanji import Kanji, KanjiStrokes
from shodoukan.repositories.fts import fts_prefix_query, fts_query
from shodoukan.repositories.mapper import kanji_strokes_to_domain, kanji_to_domain
from shodoukan.repositories.scoring import (
    KANJI_TIER_MEANING_EXACT,
    KANJI_TIER_MEANING_PHRASE,
    KANJI_TIER_MEANING_PREFIX,
    KANJI_TIER_READING_EXACT,
    KANJI_TIER_READING_PREFIX,
    KANJI_TIER_WEIGHT,
    kanji_score,
)
from shodoukan.utils.detect import contains_kana, contains_kanji
from shodoukan.utils.kana import hiragana_to_katakana, katakana_to_hiragana
from shodoukan.utils.lang import meaning_lang


# KANJIDIC2 writes on-readings in katakana and kun-readings in hiragana, so the
# query is bound twice: :q_on in katakana and :q_kun in hiragana.
_READING_SQL = (
    "EXISTS (SELECT 1 FROM json_each(kanji.on_readings) WHERE value = :q_on)"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.kun_readings) WHERE value = :q_kun)"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.kun_readings)"
    " WHERE REPLACE(value, '.', '') = :q_kun)"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.on_readings)"
    " WHERE value LIKE :q_on || '%')"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.kun_readings)"
    " WHERE value LIKE :q_kun || '.' || '%')"
)

# Evaluates to 1 for exact reading matches, 0 for prefix-only matches.
_READING_EXACT_SQL = (
    "EXISTS (SELECT 1 FROM json_each(kanji.on_readings) WHERE value = :q_on)"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.kun_readings) WHERE value = :q_kun)"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.kun_readings)"
    " WHERE REPLACE(value, '.', '') = :q_kun)"
)


def _reading_params(query: str) -> dict[str, str]:
    return {
        "q_on": hiragana_to_katakana(query),
        "q_kun": katakana_to_hiragana(query),
    }


def _with_meanings():
    return selectinload(KanjiORM.meanings)


def _popularity():
    return kanji_score(KanjiORM.jlpt, KanjiORM.freq, KanjiORM.grade)


def _meaning_join(stmt, fts_q: str, lang: str, filters: list):
    return (
        stmt.select_from(KanjiORM)
        .join(KanjiORM.meanings)
        .join(
            fts.kanji_meanings_fts,
            fts.kanji_meanings_fts.c.rowid == KanjiMeaningORM.id,
        )
        .where(
            text("kanji_meanings_fts MATCH :fts_q").bindparams(fts_q=fts_q),
            KanjiMeaningORM.lang == meaning_lang(lang),
            *filters,
        )
    )


class KanjiRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_by_literal(self, literal: str) -> Kanji | None:
        with Session(self._engine) as session:
            k = session.execute(
                select(KanjiORM)
                .options(_with_meanings())
                .where(KanjiORM.literal == literal)
            ).scalar_one_or_none()
        return kanji_to_domain(k) if k else None

    def get_strokes(self, literal: str) -> KanjiStrokes | None:
        """The KanjiVG stroke order of `literal`, or `None` if it has none.

        A CJK compatibility ideograph (神 U+FA19) falls back to its canonical
        form (神 U+795E): it's the same character, and only the canonical one
        has a drawing.
        """
        candidates = list(
            dict.fromkeys([literal, unicodedata.normalize("NFC", literal)])
        )
        with Session(self._engine) as session:
            found = {
                k.literal: k
                for k in session.execute(
                    select(KanjiSvgORM).where(KanjiSvgORM.literal.in_(candidates))
                ).scalars()
            }
            svg = next((found[c] for c in candidates if c in found), None)
            return kanji_strokes_to_domain(literal, svg) if svg else None

    def search(
        self,
        query: str | None,
        grade: int | None,
        jlpt: int | None,
        limit: int,
        offset: int,
        lang: str = "en",
    ) -> Page[Kanji]:
        if query and contains_kanji(query):
            literals = list(dict.fromkeys(ch for ch in query if contains_kanji(ch)))
            return self._search_by_literals(literals, grade, jlpt, limit, offset)

        if query and contains_kana(query):
            return self.search_ranked(
                reading_query=query, grade=grade, jlpt=jlpt, limit=limit, offset=offset
            )

        if query:
            return self.search_ranked(
                meaning_query=query,
                grade=grade,
                jlpt=jlpt,
                lang=lang,
                limit=limit,
                offset=offset,
            )

        return self._list(grade, jlpt, limit, offset)

    def search_ranked(
        self,
        reading_query: str | None = None,
        meaning_query: str | None = None,
        grade: int | None = None,
        jlpt: int | None = None,
        lang: str = "en",
        limit: int = 20,
        offset: int = 0,
    ) -> Page[Kanji]:
        """One ranked search over reading matches, meaning matches, or both.

        Every match gets `score = tier * KANJI_TIER_WEIGHT + kanji_score` (see
        `scoring.py`), so a better kind of match always ranks first and
        popularity orders kanji within a tier. A kanji found several ways keeps
        its best score. Ordering, pagination and the total are done in SQL.
        """
        filters = self._grade_jlpt_conds(grade, jlpt)
        branches = []
        if reading_query:
            branches.append(self._reading_matches(reading_query, filters))
        if meaning_query:
            branches.append(self._meaning_matches(meaning_query, lang, filters))
        if not branches:
            return Page(items=[], total=0, limit=limit, offset=offset)

        hits = union_all(*branches).subquery("hits")
        best = (
            select(hits.c.literal, func.max(hits.c.score).label("score"))
            .group_by(hits.c.literal)
            .subquery("best")
        )
        page_stmt = (
            select(best.c.literal, func.count().over().label("total"))
            .order_by(desc(best.c.score), best.c.literal)
            .limit(limit)
            .offset(offset)
        )

        with Session(self._engine) as session:
            rows = session.execute(page_stmt).all()
            if rows:
                total = rows[0].total
            else:
                total = session.execute(select(func.count()).select_from(best)).scalar()
            items = self._load_by_literals(session, [r.literal for r in rows])

        return Page(items=items, total=total or 0, limit=limit, offset=offset)

    def _reading_matches(self, query: str, filters: list):
        """Kanji with a reading equal to (tier 3) or starting with (2) `query`."""
        params = _reading_params(query)
        tier = case(
            (text(_READING_EXACT_SQL).bindparams(**params), KANJI_TIER_READING_EXACT),
            else_=KANJI_TIER_READING_PREFIX,
        )
        return select(
            KanjiORM.literal.label("literal"),
            (tier * KANJI_TIER_WEIGHT + _popularity()).label("score"),
        ).where(text(_READING_SQL).bindparams(**params), *filters)

    def _meaning_matches(self, query: str, lang: str, filters: list):
        """Kanji with a meaning in `lang` matching `query` (FTS).

        A meaning equal to the query is tier 3 and one containing it as a
        phrase tier 2. When the phrase matches nothing, word prefixes are
        tried instead ("au" → "audacious"), all tier 1: they share only a few
        letters with the query.
        """
        fts_q = fts_query(query)
        if self._meaning_phrase_exists(fts_q, lang, filters):
            exact = func.lower(KanjiMeaningORM.text) == query.lower()
            tier = func.max(
                case(
                    (exact, KANJI_TIER_MEANING_EXACT),
                    else_=KANJI_TIER_MEANING_PHRASE,
                )
            )
        else:
            fts_q = fts_prefix_query(query)
            tier = sql_literal(KANJI_TIER_MEANING_PREFIX)
        return _meaning_join(
            select(
                KanjiORM.literal.label("literal"),
                (tier * KANJI_TIER_WEIGHT + _popularity()).label("score"),
            ),
            fts_q,
            lang,
            filters,
        ).group_by(KanjiORM.literal)

    def _meaning_phrase_exists(self, fts_q: str, lang: str, filters: list) -> bool:
        stmt = _meaning_join(select(KanjiORM.literal), fts_q, lang, filters).limit(1)
        with Session(self._engine) as session:
            return session.execute(stmt).first() is not None

    def _search_by_literals(
        self,
        literals: list[str],
        grade: int | None,
        jlpt: int | None,
        limit: int,
        offset: int,
    ) -> Page[Kanji]:
        extra = self._grade_jlpt_conds(grade, jlpt)
        where = and_(KanjiORM.literal.in_(literals), *extra)
        with Session(self._engine) as session:
            total = session.execute(
                select(func.count()).select_from(KanjiORM).where(where)
            ).scalar() or 0
            result_literals = session.execute(
                select(KanjiORM.literal)
                .where(where)
                .order_by(desc(_popularity()))
                .limit(limit)
                .offset(offset)
            ).scalars().all()
            items = self._load_by_literals(session, list(result_literals))
        return Page(items=items, total=total, limit=limit, offset=offset)

    def _list(
        self, grade: int | None, jlpt: int | None, limit: int, offset: int
    ) -> Page[Kanji]:
        """All kanji (optionally filtered by grade / JLPT), most popular first."""
        extra = self._grade_jlpt_conds(grade, jlpt)
        where_clause = and_(*extra) if extra else true()
        with Session(self._engine) as session:
            total = session.execute(
                select(func.count()).select_from(KanjiORM).where(where_clause)
            ).scalar() or 0
            literals = session.execute(
                select(KanjiORM.literal)
                .where(where_clause)
                .order_by(desc(_popularity()))
                .limit(limit)
                .offset(offset)
            ).scalars().all()
            items = self._load_by_literals(session, list(literals))
        return Page(items=items, total=total, limit=limit, offset=offset)

    def _grade_jlpt_conds(self, grade: int | None, jlpt: int | None) -> list:
        conds = []
        if grade is not None:
            conds.append(KanjiORM.grade == grade)
        if jlpt is not None:
            conds.append(KanjiORM.jlpt == jlpt)
        return conds

    def get_by_literals(self, literals: list[str]) -> list[Kanji]:
        with Session(self._engine) as session:
            return self._load_by_literals(session, literals)

    def _load_by_literals(self, session: Session, literals: list[str]) -> list[Kanji]:
        if not literals:
            return []
        kanji_map = {
            k.literal: kanji_to_domain(k)
            for k in session.execute(
                select(KanjiORM)
                .options(_with_meanings())
                .where(KanjiORM.literal.in_(literals))
            ).scalars().all()
        }
        return [kanji_map[lit] for lit in literals if lit in kanji_map]
