from collections.abc import Iterable
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Select,
    SQLColumnExpression,
    Subquery,
    exists,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ...domain.entities import EntryCollection, PracticeEntry
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import PracticeEntryRepository
from ...domain.searches import (
    InCollection,
    LibrarySearch,
    NotInCollection,
    SearchScope,
)
from ..db.mappers import practice_entry_to_db, practice_entry_to_domain
from ..db.orm import (
    PracticeEntryKanjiReadingORM,
    PracticeEntryORM,
    PracticeEntryReadingORM,
    PracticeExampleORM,
    PracticeGlossORM,
    PracticeSenseORM,
    entry_collection_items,
)
from .sqlalchemy_library_search import best_matches, meaning_match, text_match

Q = TypeVar("Q", bound=Select[Any])

# Load the whole nested snapshot up front, one query per level (no N+1).
_LOAD = (
    selectinload(PracticeEntryORM.kanji_readings),
    selectinload(PracticeEntryORM.readings),
    selectinload(PracticeEntryORM.senses).selectinload(PracticeSenseORM.glosses),
    selectinload(PracticeEntryORM.senses)
    .selectinload(PracticeSenseORM.examples)
    .selectinload(PracticeExampleORM.sentences),
)


class SqlAlchemyPracticeEntryRepository(PracticeEntryRepository):
    """Flushes but never commits: the caller owns the transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, entry_id: int, user_id: UUID) -> PracticeEntry | None:
        query = self._select().where(
            PracticeEntryORM.id == entry_id, PracticeEntryORM.user_id == user_id
        )
        row = self._session.scalars(query).one_or_none()
        return practice_entry_to_domain(row) if row else None

    def get_many(self, ids: Iterable[int], user_id: UUID) -> list[PracticeEntry]:
        query = (
            self._select()
            .where(
                PracticeEntryORM.id.in_(list(ids)), PracticeEntryORM.user_id == user_id
            )
            .order_by(PracticeEntryORM.id)
        )
        return [practice_entry_to_domain(row) for row in self._session.scalars(query)]

    def find(
        self,
        user_id: UUID,
        search: LibrarySearch,
        scope: SearchScope[EntryCollection],
        limit: int,
        offset: int,
    ) -> list[PracticeEntry]:
        query = self._search(self._select(), user_id, search, scope, ordered=True)
        rows = self._session.scalars(query.limit(limit).offset(offset))
        return [practice_entry_to_domain(row) for row in rows]

    def count(
        self,
        user_id: UUID,
        search: LibrarySearch,
        scope: SearchScope[EntryCollection],
    ) -> int:
        query = select(func.count()).select_from(PracticeEntryORM)
        query = self._search(query, user_id, search, scope, ordered=False)
        return self._session.scalar(query) or 0

    def get_by_source_entry_id(
        self, source_entry_id: int, user_id: UUID
    ) -> PracticeEntry | None:
        query = self._select().where(
            PracticeEntryORM.source_entry_id == source_entry_id,
            PracticeEntryORM.user_id == user_id,
        )
        row = self._session.scalars(query).one_or_none()
        return practice_entry_to_domain(row) if row else None

    def practice_ids_by_source_entry_id(
        self, source_entry_ids: Iterable[int], user_id: UUID
    ) -> dict[int, int]:
        query = select(PracticeEntryORM.source_entry_id, PracticeEntryORM.id).where(
            PracticeEntryORM.source_entry_id.in_(list(source_entry_ids)),
            PracticeEntryORM.user_id == user_id,
        )
        rows = self._session.execute(query).tuples().all()
        # The IN leaves the user's own words (no source) out; this tells mypy.
        return {source: id_ for source, id_ in rows if source is not None}

    def add_if_absent(self, entry: PracticeEntry) -> tuple[PracticeEntry, bool]:
        if entry.source_entry_id is None:
            raise ValueError("only dictionary entries are added if absent")
        row = practice_entry_to_db(entry)
        try:
            # Savepoint: a unique-constraint clash (a concurrent import of the
            # same item) rolls back only this insert, not the caller's work.
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError:
            existing = self.get_by_source_entry_id(entry.source_entry_id, entry.user_id)
            if existing is None:
                raise
            return existing, False
        return practice_entry_to_domain(row), True

    def add(self, entry: PracticeEntry) -> PracticeEntry:
        row = practice_entry_to_db(entry)
        self._session.add(row)
        self._session.flush()
        return practice_entry_to_domain(row)

    def update(self, entry: PracticeEntry) -> PracticeEntry:
        """Replace the stored snapshot with `entry`.

        Nested items with an id are updated, items without one are inserted
        and stored items missing from `entry` are deleted.
        """
        self._require_row(entry)
        row = self._session.merge(practice_entry_to_db(entry))
        self._session.flush()
        return practice_entry_to_domain(row)

    def delete(self, entry: PracticeEntry) -> None:
        """Delete the row; its nested rows and collection links cascade."""
        self._session.delete(self._require_row(entry))
        self._session.flush()

    def _require_row(self, entry: PracticeEntry) -> PracticeEntryORM:
        stored = self._session.get(PracticeEntryORM, entry.id) if entry.id else None
        if stored is None or stored.user_id != entry.user_id:
            raise EntityNotFoundError(f"entry {entry.id} not found")
        return stored

    def _search(
        self,
        query: Q,
        user_id: UUID,
        search: LibrarySearch,
        scope: SearchScope[EntryCollection],
        *,
        ordered: bool,
    ) -> Q:
        """`query` narrowed to the search and its scope, best match first."""
        query = query.where(*self._user_filter(user_id, search.active))
        order: list[SQLColumnExpression[Any]] = [
            PracticeEntryORM.created_at.desc(),
            PracticeEntryORM.id.desc(),
        ]
        items = entry_collection_items
        match scope:
            case InCollection(collection=collection):
                query = query.join(
                    items, items.c.entry_id == PracticeEntryORM.id
                ).where(items.c.collection_id == collection.id)
                order = [items.c.added_at, PracticeEntryORM.id]
            case NotInCollection(collection=collection):
                query = query.where(
                    ~exists().where(
                        items.c.entry_id == PracticeEntryORM.id,
                        items.c.collection_id == collection.id,
                    )
                )
        if search.text:
            matches = self._matches(user_id, search, search.text)
            query = query.join(matches, matches.c.item_id == PracticeEntryORM.id)
            order = [matches.c.tier.desc(), *order]
        return query.order_by(*order) if ordered else query

    @staticmethod
    def _matches(user_id: UUID, search: LibrarySearch, text: str) -> Subquery:
        """Each of the user's entries that matches, with its best tier."""
        owned = PracticeEntryORM.user_id == user_id
        spelling, spelling_tier = text_match(
            PracticeEntryKanjiReadingORM.kanji, search.needles
        )
        reading, reading_tier = text_match(PracticeEntryReadingORM.text, search.needles)
        meaning, meaning_tier = meaning_match(PracticeGlossORM.text, text)
        meaning_conditions = [meaning]
        if search.meaning_lang:
            meaning_conditions.append(PracticeGlossORM.lang == search.meaning_lang)
        return best_matches(
            [
                select(
                    PracticeEntryKanjiReadingORM.entry_id.label("item_id"),
                    spelling_tier.label("tier"),
                )
                .join(PracticeEntryORM)
                .where(owned, spelling),
                select(
                    PracticeEntryReadingORM.entry_id.label("item_id"),
                    reading_tier.label("tier"),
                )
                .join(PracticeEntryORM)
                .where(owned, reading),
                select(
                    PracticeSenseORM.entry_id.label("item_id"),
                    meaning_tier.label("tier"),
                )
                .join(PracticeGlossORM)
                .join(PracticeEntryORM)
                .where(owned, *meaning_conditions),
            ]
        )

    @staticmethod
    def _user_filter(user_id: UUID, active: bool | None) -> list[ColumnElement[bool]]:
        conditions = [PracticeEntryORM.user_id == user_id]
        if active is not None:
            conditions.append(PracticeEntryORM.is_active.is_(active))
        return conditions

    def _select(self) -> Select[PracticeEntryORM]:
        return select(PracticeEntryORM).options(*_LOAD)
