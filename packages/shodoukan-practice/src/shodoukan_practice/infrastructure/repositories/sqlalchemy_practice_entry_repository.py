from collections.abc import Iterable

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from ...domain.entities import EntryCollection, PracticeEntry
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import PracticeEntryRepository
from ..db.mappers import practice_entry_to_db, practice_entry_to_domain
from ..db.orm import (
    PracticeEntryORM,
    PracticeExampleORM,
    PracticeSenseORM,
    entry_collection_items,
)

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

    def get(self, entry_id: int, user_id: int) -> PracticeEntry | None:
        query = self._select().where(
            PracticeEntryORM.id == entry_id, PracticeEntryORM.user_id == user_id
        )
        row = self._session.scalars(query).one_or_none()
        return practice_entry_to_domain(row) if row else None

    def get_many(self, ids: Iterable[int], user_id: int) -> list[PracticeEntry]:
        query = (
            self._select()
            .where(
                PracticeEntryORM.id.in_(list(ids)), PracticeEntryORM.user_id == user_id
            )
            .order_by(PracticeEntryORM.id)
        )
        return [practice_entry_to_domain(row) for row in self._session.scalars(query)]

    def list_by_collection(
        self, collection: EntryCollection, limit: int, offset: int
    ) -> list[PracticeEntry]:
        query = (
            self._select()
            .join(
                entry_collection_items,
                entry_collection_items.c.entry_id == PracticeEntryORM.id,
            )
            .where(
                entry_collection_items.c.collection_id == collection.id,
                PracticeEntryORM.user_id == collection.user_id,
                PracticeEntryORM.is_active.is_(True),
            )
            .order_by(entry_collection_items.c.added_at, PracticeEntryORM.id)
            .limit(limit)
            .offset(offset)
        )
        return [practice_entry_to_domain(row) for row in self._session.scalars(query)]

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
        stored = self._session.get(PracticeEntryORM, entry.id) if entry.id else None
        if stored is None or stored.user_id != entry.user_id:
            raise EntityNotFoundError(f"entry {entry.id} not found")
        row = self._session.merge(practice_entry_to_db(entry))
        self._session.flush()
        return practice_entry_to_domain(row)

    def _select(self) -> Select[tuple[PracticeEntryORM]]:
        return select(PracticeEntryORM).options(*_LOAD)
