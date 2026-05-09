from sqlalchemy import and_, distinct, func, select, text, true
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from shodoukan.db import schema as fts
from shodoukan.db.orm import KanjiMeaningORM, KanjiORM
from shodoukan.models.entry import Page
from shodoukan.models.kanji import Kanji
from shodoukan.repositories.mapper import kanji_to_domain
from shodoukan.utils.detect import contains_kana, contains_kanji


def _fts_query(query: str) -> str:
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


def _fts_prefix_query(query: str) -> str:
    return " ".join(f"{word}*" for word in query.split())


_READING_SQL = (
    "EXISTS (SELECT 1 FROM json_each(kanji.on_readings) WHERE value = :q)"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.kun_readings) WHERE value = :q)"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.on_readings)"
    " WHERE value LIKE :q || '%')"
    " OR EXISTS (SELECT 1 FROM json_each(kanji.kun_readings)"
    " WHERE value LIKE :q || '.' || '%')"
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
    ) -> Page[Kanji]:
        if query and len(query) == 1 and contains_kanji(query):
            k = self.get_by_literal(query)
            if k is None:
                return Page(items=[], total=0, limit=limit, offset=offset)
            if grade is not None and k.grade != grade:
                return Page(items=[], total=0, limit=limit, offset=offset)
            if jlpt is not None and k.jlpt != jlpt:
                return Page(items=[], total=0, limit=limit, offset=offset)
            return Page(items=[k], total=1, limit=limit, offset=offset)

        if query and contains_kana(query):
            return self._search_by_reading(query, grade, jlpt, limit, offset)

        return self._search_by_meaning(query, grade, jlpt, limit, offset)

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
        with Session(self._engine) as session:
            total = session.execute(
                select(func.count()).select_from(KanjiORM).where(where_clause)
            ).scalar() or 0
            items = session.execute(
                select(KanjiORM)
                .options(_with_meanings())
                .where(where_clause)
                .limit(limit)
                .offset(offset)
            ).scalars().all()
        return Page(
            items=[kanji_to_domain(k) for k in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def _search_by_meaning(
        self,
        query: str | None,
        grade: int | None,
        jlpt: int | None,
        limit: int,
        offset: int,
    ) -> Page[Kanji]:
        extra = self._grade_jlpt_conds(grade, jlpt)

        if query:
            def _build(fts_q: str):
                fts_where = and_(
                    text("kanji_meanings_fts MATCH :fts_q").bindparams(fts_q=fts_q),
                    KanjiMeaningORM.lang == "en",
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

                return (
                    base(select(KanjiORM.literal).distinct())
                    .order_by(text("rank"))
                    .limit(limit)
                    .offset(offset),
                    base(select(func.count(distinct(KanjiORM.literal)))),
                )

            with Session(self._engine) as session:
                id_stmt, count_stmt = _build(_fts_query(query))
                literals = session.execute(id_stmt).scalars().all()
                total = session.execute(count_stmt).scalar() or 0
                if not literals:
                    id_stmt, count_stmt = _build(_fts_prefix_query(query))
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
                        .limit(limit)
                        .offset(offset)
                    ).scalars().all(),
                )

        return Page(items=items, total=total, limit=limit, offset=offset)

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
