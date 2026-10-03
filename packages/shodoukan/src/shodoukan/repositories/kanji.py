from sqlalchemy import and_, case, desc, distinct, func, select, text, true
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from shodoukan.db import schema as fts
from shodoukan.db.orm import KanjiMeaningORM, KanjiORM
from shodoukan.models.entry import Page
from shodoukan.models.kanji import Kanji
from shodoukan.repositories.fts import fts_prefix_query, fts_query
from shodoukan.repositories.mapper import kanji_to_domain
from shodoukan.repositories.scoring import FTS_KANJI_WEIGHT, kanji_score
from shodoukan.utils.detect import contains_kana, contains_kanji
from shodoukan.utils.lang import meaning_lang


_READING_SQL = (
    "EXISTS (SELECT 1 FROM json_each(kanji.on_readings) WHERE value = :q)"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.kun_readings) WHERE value = :q)"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.kun_readings)"
    " WHERE REPLACE(value, '.', '') = :q)"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.on_readings)"
    " WHERE value LIKE :q || '%')"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.kun_readings)"
    " WHERE value LIKE :q || '.' || '%')"
)

# Evaluates to 1 for exact reading matches, 0 for prefix-only matches.
_READING_EXACT_SQL = (
    "EXISTS (SELECT 1 FROM json_each(kanji.on_readings) WHERE value = :q)"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.kun_readings) WHERE value = :q)"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.kun_readings)"
    " WHERE REPLACE(value, '.', '') = :q)"
)


def _with_meanings():
    return selectinload(KanjiORM.meanings)


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
            return self._search_by_reading(query, grade, jlpt, limit, offset)

        return self._search_by_meaning(query, grade, jlpt, limit, offset, lang=lang)

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
        score = kanji_score(KanjiORM.jlpt, KanjiORM.freq, KanjiORM.grade)
        with Session(self._engine) as session:
            total = session.execute(
                select(func.count()).select_from(KanjiORM).where(where)
            ).scalar() or 0
            result_literals = session.execute(
                select(KanjiORM.literal)
                .where(where)
                .order_by(desc(score))
                .limit(limit)
                .offset(offset)
            ).scalars().all()
            items = self._load_by_literals(session, list(result_literals))
        return Page(items=items, total=total, limit=limit, offset=offset)

    def _grade_jlpt_conds(self, grade: int | None, jlpt: int | None) -> list:
        conds = []
        if grade is not None:
            conds.append(KanjiORM.grade == grade)
        if jlpt is not None:
            conds.append(KanjiORM.jlpt == jlpt)
        return conds

    def _search_by_reading(
        self, query: str, grade: int | None, jlpt: int | None, limit: int, offset: int
    ) -> Page[Kanji]:
        where_clause = and_(
            text(_READING_SQL).bindparams(q=query),
            *self._grade_jlpt_conds(grade, jlpt),
        )
        exact_case = case(
            (text(_READING_EXACT_SQL).bindparams(q=query), 1), else_=0
        )
        with Session(self._engine) as session:
            total = session.execute(
                select(func.count()).select_from(KanjiORM).where(where_clause)
            ).scalar() or 0
            literals = session.execute(
                select(KanjiORM.literal)
                .where(where_clause)
                .order_by(desc(exact_case), desc(kanji_score(
                    KanjiORM.jlpt, KanjiORM.freq, KanjiORM.grade
                )))
                .limit(limit)
                .offset(offset)
            ).scalars().all()
            items = self._load_by_literals(session, list(literals))
        return Page(items=items, total=total, limit=limit, offset=offset)

    def _search_by_meaning(
        self,
        query: str | None,
        grade: int | None,
        jlpt: int | None,
        limit: int,
        offset: int,
        lang: str = "en",
    ) -> Page[Kanji]:
        extra = self._grade_jlpt_conds(grade, jlpt)

        if query:
            def _build(fts_q: str):
                fts_where = and_(
                    text("kanji_meanings_fts MATCH :fts_q").bindparams(fts_q=fts_q),
                    KanjiMeaningORM.lang == meaning_lang(lang),
                    *extra,
                )

                def base(s):
                    return (
                        s.select_from(KanjiORM)
                        .join(KanjiORM.meanings)
                        .join(
                            fts.kanji_meanings_fts,
                            fts.kanji_meanings_fts.c.rowid == KanjiMeaningORM.id,
                        )
                        .where(fts_where)
                    )

                _fts_boost = func.min(text("rank")) * (-FTS_KANJI_WEIGHT)
                _combined = (
                    kanji_score(KanjiORM.jlpt, KanjiORM.freq, KanjiORM.grade)
                    + _fts_boost
                )
                return (
                    base(select(KanjiORM.literal))
                    .group_by(KanjiORM.literal)
                    .order_by(desc(_combined))
                    .limit(limit)
                    .offset(offset),
                    base(select(func.count(distinct(KanjiORM.literal)))),
                )

            with Session(self._engine) as session:
                id_stmt, count_stmt = _build(fts_query(query))
                literals = session.execute(id_stmt).scalars().all()
                total = session.execute(count_stmt).scalar() or 0
                if not literals:
                    id_stmt, count_stmt = _build(fts_prefix_query(query))
                    literals = session.execute(id_stmt).scalars().all()
                    total = session.execute(count_stmt).scalar() or 0
                items = self._load_by_literals(session, list(literals))
        else:
            where_clause = and_(*extra) if extra else true()
            with Session(self._engine) as session:
                total = session.execute(
                    select(func.count()).select_from(KanjiORM).where(where_clause)
                ).scalar() or 0
                items = self._load_by_literals(
                    session,
                    session.execute(
                        select(KanjiORM.literal)
                        .where(where_clause)
                        .order_by(desc(kanji_score(
                            KanjiORM.jlpt, KanjiORM.freq, KanjiORM.grade
                        )))
                        .limit(limit)
                        .offset(offset)
                    ).scalars().all(),
                )

        return Page(items=items, total=total, limit=limit, offset=offset)

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
