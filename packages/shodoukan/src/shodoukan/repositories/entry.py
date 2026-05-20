from sqlalchemy import and_, case, desc, distinct, func, or_, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from shodoukan.db import schema as fts
from shodoukan.db.orm import (
    EntryKanjiORM,
    EntryORM,
    ExampleORM,
    GlossORM,
    KanjiReadingORM,
    ReadingORM,
    SenseORM,
)
from shodoukan.models.entry import Entry, EntryKanjiLink, Page
from shodoukan.repositories.mapper import entry_to_domain


def _priority_score(field):
    """Numeric score derived from a JMDict priority JSON field."""
    safe = func.coalesce(field, "[]")
    return sum(
        case((func.instr(safe, code) > 0, pts), else_=0)
        for code, pts in [
            ("ichi1", 200), ("news1", 200), ("spec1", 200), ("gai1", 200),
            ("ichi2", 100), ("news2", 100), ("spec2", 100), ("gai2", 100),
        ]
    )


def _fts_query(query: str) -> str:
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


def _fts_prefix_query(query: str) -> str:
    return " ".join(f"{word}*" for word in query.split())


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
            ReadingORM.text == query,
            ReadingORM.text.like(prefix),
        )
        exact = or_(
            KanjiReadingORM.kanji == query,
            ReadingORM.text == query,
        )
        priority = func.max(
            _priority_score(KanjiReadingORM.priority)
            + _priority_score(ReadingORM.priority)
        ).label("priority")

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
            entry_ids = session.execute(
                base(
                    select(
                        EntryORM.id,
                        func.max(exact).label("exact_match"),
                        priority,
                    )
                )
                .group_by(EntryORM.id)
                .order_by(desc("exact_match"), desc("priority"))
                .limit(limit)
                .offset(offset)
            ).scalars().all()
            items = self._hydrate(session, entry_ids)

        return Page(items=items, total=total, limit=limit, offset=offset)

    def search_by_english(self, query: str, limit: int, offset: int) -> Page[Entry]:
        def _build(fts_q: str):
            fts_where = and_(
                text("glosses_fts MATCH :fts_q").bindparams(fts_q=fts_q),
                GlossORM.lang == "eng",
            )

            def base(s):
                return (
                    s.select_from(EntryORM)
                    .join(EntryORM.senses)
                    .join(SenseORM.glosses)
                    .join(fts.glosses_fts, fts.glosses_fts.c.rowid == GlossORM.id)
                    .where(fts_where)
                )

            return (
                base(select(distinct(EntryORM.id)))
                .order_by(text("rank"))
                .limit(limit)
                .offset(offset),
                base(select(func.count(distinct(EntryORM.id)))),
            )

        with Session(self._engine) as session:
            id_stmt, count_stmt = _build(_fts_query(query))
            entry_ids = session.execute(id_stmt).scalars().all()
            total = session.execute(count_stmt).scalar() or 0
            if not entry_ids:
                id_stmt, count_stmt = _build(_fts_prefix_query(query))
                entry_ids = session.execute(id_stmt).scalars().all()
                total = session.execute(count_stmt).scalar() or 0
            items = self._hydrate(session, list(entry_ids))

        return Page(items=items, total=total, limit=limit, offset=offset)

    def get_kanji_for_entry(self, entry_id: int) -> list[EntryKanjiLink]:
        with Session(self._engine) as session:
            rows = session.execute(
                select(EntryKanjiORM.literal, EntryKanjiORM.priority_score)
                .where(EntryKanjiORM.entry_id == entry_id)
                .order_by(desc(EntryKanjiORM.priority_score))
            ).all()
        return [
            EntryKanjiLink(literal=r.literal, priority_score=r.priority_score)
            for r in rows
        ]

    def get_entries_for_kanji(
        self, literal: str, limit: int, offset: int
    ) -> Page[Entry]:
        with Session(self._engine) as session:
            total = session.execute(
                select(func.count()).where(EntryKanjiORM.literal == literal)
            ).scalar() or 0
            entry_ids = session.execute(
                select(EntryKanjiORM.entry_id)
                .where(EntryKanjiORM.literal == literal)
                .order_by(desc(EntryKanjiORM.priority_score))
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
                    EntryKanjiORM.literal,
                    func.max(EntryKanjiORM.priority_score).label("score"),
                )
                .where(EntryKanjiORM.entry_id.in_(entry_ids))
                .group_by(EntryKanjiORM.literal)
                .order_by(desc("score"))
                .limit(limit)
            ).all()
        return [r.literal for r in rows]

    def _hydrate(self, session: Session, entry_ids: list[int]) -> list[Entry]:
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
        return [entry_to_domain(entries[eid]) for eid in entry_ids if eid in entries]
