from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ...domain.entities import KanjiCollection, PracticeKanji
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import PracticeKanjiRepository
from ..db.mappers import practice_kanji_to_db, practice_kanji_to_domain
from ..db.orm import PracticeKanjiORM, kanji_collection_items

# Load the whole nested snapshot up front, one query per level (no N+1).
_LOAD = (
    selectinload(PracticeKanjiORM.reading_items),
    selectinload(PracticeKanjiORM.meanings),
)


class SqlAlchemyPracticeKanjiRepository(PracticeKanjiRepository):
    """Flushes but never commits: the caller owns the transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, kanji_id: int, user_id: UUID) -> PracticeKanji | None:
        query = self._select().where(
            PracticeKanjiORM.id == kanji_id, PracticeKanjiORM.user_id == user_id
        )
        row = self._session.scalars(query).one_or_none()
        return practice_kanji_to_domain(row) if row else None

    def get_many(self, ids: Iterable[int], user_id: UUID) -> list[PracticeKanji]:
        query = (
            self._select()
            .where(
                PracticeKanjiORM.id.in_(list(ids)), PracticeKanjiORM.user_id == user_id
            )
            .order_by(PracticeKanjiORM.id)
        )
        return [practice_kanji_to_domain(row) for row in self._session.scalars(query)]

    def list_for_user(
        self, user_id: UUID, limit: int, offset: int, active: bool | None = None
    ) -> list[PracticeKanji]:
        query = (
            self._select()
            .where(*self._user_filter(user_id, active))
            .order_by(PracticeKanjiORM.created_at.desc(), PracticeKanjiORM.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [practice_kanji_to_domain(row) for row in self._session.scalars(query)]

    def count_for_user(self, user_id: UUID, active: bool | None = None) -> int:
        query = select(func.count()).where(*self._user_filter(user_id, active))
        return self._session.scalar(query.select_from(PracticeKanjiORM)) or 0

    def list_by_collection(
        self, collection: KanjiCollection, limit: int, offset: int
    ) -> list[PracticeKanji]:
        query = (
            self._select()
            .join(
                kanji_collection_items,
                kanji_collection_items.c.kanji_id == PracticeKanjiORM.id,
            )
            .where(
                kanji_collection_items.c.collection_id == collection.id,
                PracticeKanjiORM.user_id == collection.user_id,
                PracticeKanjiORM.is_active.is_(True),
            )
            .order_by(kanji_collection_items.c.added_at, PracticeKanjiORM.id)
            .limit(limit)
            .offset(offset)
        )
        return [practice_kanji_to_domain(row) for row in self._session.scalars(query)]

    def get_by_literal(self, literal: str, user_id: UUID) -> PracticeKanji | None:
        query = self._select().where(
            PracticeKanjiORM.literal == literal, PracticeKanjiORM.user_id == user_id
        )
        row = self._session.scalars(query).one_or_none()
        return practice_kanji_to_domain(row) if row else None

    def practice_ids_by_literal(
        self, literals: Iterable[str], user_id: UUID
    ) -> dict[str, int]:
        query = select(PracticeKanjiORM.literal, PracticeKanjiORM.id).where(
            PracticeKanjiORM.literal.in_(list(literals)),
            PracticeKanjiORM.user_id == user_id,
        )
        return dict(self._session.execute(query).tuples().all())

    def add_if_absent(self, kanji: PracticeKanji) -> tuple[PracticeKanji, bool]:
        row = practice_kanji_to_db(kanji)
        try:
            # Savepoint: a unique-constraint clash (a concurrent import of the
            # same item) rolls back only this insert, not the caller's work.
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError:
            existing = self.get_by_literal(kanji.literal, kanji.user_id)
            if existing is None:
                raise
            return existing, False
        return practice_kanji_to_domain(row), True

    def add(self, kanji: PracticeKanji) -> PracticeKanji:
        row = practice_kanji_to_db(kanji)
        self._session.add(row)
        self._session.flush()
        return practice_kanji_to_domain(row)

    def update(self, kanji: PracticeKanji) -> PracticeKanji:
        """Replace the stored snapshot with `kanji`.

        Nested items with an id are updated, items without one are inserted
        and stored items missing from `kanji` are deleted.
        """
        stored = self._session.get(PracticeKanjiORM, kanji.id) if kanji.id else None
        if stored is None or stored.user_id != kanji.user_id:
            raise EntityNotFoundError(f"kanji {kanji.id} not found")
        row = self._session.merge(practice_kanji_to_db(kanji))
        self._session.flush()
        return practice_kanji_to_domain(row)

    @staticmethod
    def _user_filter(user_id: UUID, active: bool | None) -> list[ColumnElement[bool]]:
        conditions = [PracticeKanjiORM.user_id == user_id]
        if active is not None:
            conditions.append(PracticeKanjiORM.is_active.is_(active))
        return conditions

    def _select(self) -> Select[tuple[PracticeKanjiORM]]:
        return select(PracticeKanjiORM).options(*_LOAD)
