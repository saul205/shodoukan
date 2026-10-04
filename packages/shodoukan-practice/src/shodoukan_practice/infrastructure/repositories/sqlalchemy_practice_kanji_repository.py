from collections.abc import Iterable
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Select,
    SQLColumnExpression,
    String,
    Subquery,
    case,
    exists,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ...domain.entities import KanjiCollection, PracticeKanji
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import PracticeKanjiRepository
from ...domain.searches import (
    InCollection,
    LibrarySearch,
    MatchTier,
    NotInCollection,
    SearchScope,
)
from ..db.mappers import practice_kanji_to_db, practice_kanji_to_domain
from ..db.orm import (
    PracticeKanjiMeaningORM,
    PracticeKanjiORM,
    PracticeKanjiReadingItemORM,
    kanji_collection_items,
)
from .sqlalchemy_library_search import best_matches, meaning_match, text_match

Q = TypeVar("Q", bound=Select[Any])

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

    def find(
        self,
        user_id: UUID,
        search: LibrarySearch,
        scope: SearchScope[KanjiCollection],
        limit: int,
        offset: int,
    ) -> list[PracticeKanji]:
        query = self._search(self._select(), user_id, search, scope, ordered=True)
        rows = self._session.scalars(query.limit(limit).offset(offset))
        return [practice_kanji_to_domain(row) for row in rows]

    def count(
        self,
        user_id: UUID,
        search: LibrarySearch,
        scope: SearchScope[KanjiCollection],
    ) -> int:
        query = select(func.count()).select_from(PracticeKanjiORM)
        query = self._search(query, user_id, search, scope, ordered=False)
        return self._session.scalar(query) or 0

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
        self._require_row(kanji)
        row = self._session.merge(practice_kanji_to_db(kanji))
        self._session.flush()
        return practice_kanji_to_domain(row)

    def delete(self, kanji: PracticeKanji) -> None:
        """Delete the row; its nested rows and collection links cascade."""
        self._session.delete(self._require_row(kanji))
        self._session.flush()

    def _require_row(self, kanji: PracticeKanji) -> PracticeKanjiORM:
        stored = self._session.get(PracticeKanjiORM, kanji.id) if kanji.id else None
        if stored is None or stored.user_id != kanji.user_id:
            raise EntityNotFoundError(f"kanji {kanji.id} not found")
        return stored

    def _search(
        self,
        query: Q,
        user_id: UUID,
        search: LibrarySearch,
        scope: SearchScope[KanjiCollection],
        *,
        ordered: bool,
    ) -> Q:
        """`query` narrowed to the search and its scope, best match first."""
        query = query.where(*self._user_filter(user_id, search.active))
        order: list[SQLColumnExpression[Any]] = [
            PracticeKanjiORM.created_at.desc(),
            PracticeKanjiORM.id.desc(),
        ]
        items = kanji_collection_items
        match scope:
            case InCollection(collection=collection):
                query = query.join(
                    items, items.c.kanji_id == PracticeKanjiORM.id
                ).where(items.c.collection_id == collection.id)
                order = [items.c.added_at, PracticeKanjiORM.id]
            case NotInCollection(collection=collection):
                query = query.where(
                    ~exists().where(
                        items.c.kanji_id == PracticeKanjiORM.id,
                        items.c.collection_id == collection.id,
                    )
                )
        if search.text:
            matches = self._matches(user_id, search, search.text)
            query = query.join(matches, matches.c.item_id == PracticeKanjiORM.id)
            order = [matches.c.tier.desc(), *order]
        return query.order_by(*order) if ordered else query

    @staticmethod
    def _matches(user_id: UUID, search: LibrarySearch, text: str) -> Subquery:
        """Each of the user's kanji that matches, with its best tier.

        The literal is EXACT when it's the query and PREFIX when the query
        contains it (兄弟 finds 兄 and 弟). Readings are compared without
        their okurigana dot and affix dash (`た.べる`, `-あ.う`).
        """
        owned = PracticeKanjiORM.user_id == user_id
        in_query = literal(text, String).contains(PracticeKanjiORM.literal)
        literal_tier = case(
            (PracticeKanjiORM.literal == text, MatchTier.EXACT.value),
            else_=MatchTier.PREFIX.value,
        )
        bare_reading = func.replace(
            func.replace(PracticeKanjiReadingItemORM.text, ".", ""), "-", ""
        )
        reading, reading_tier = text_match(bare_reading, search.needles)
        meaning, meaning_tier = meaning_match(PracticeKanjiMeaningORM.text, text)
        meaning_conditions = [meaning]
        if search.meaning_lang:
            meaning_conditions.append(
                PracticeKanjiMeaningORM.lang == search.meaning_lang
            )
        return best_matches(
            [
                select(
                    PracticeKanjiORM.id.label("item_id"), literal_tier.label("tier")
                ).where(owned, or_(PracticeKanjiORM.literal == text, in_query)),
                select(
                    PracticeKanjiReadingItemORM.kanji_id.label("item_id"),
                    reading_tier.label("tier"),
                )
                .join(PracticeKanjiORM)
                .where(owned, reading),
                select(
                    PracticeKanjiMeaningORM.kanji_id.label("item_id"),
                    meaning_tier.label("tier"),
                )
                .join(PracticeKanjiORM)
                .where(owned, *meaning_conditions),
            ]
        )

    @staticmethod
    def _user_filter(user_id: UUID, active: bool | None) -> list[ColumnElement[bool]]:
        conditions = [PracticeKanjiORM.user_id == user_id]
        if active is not None:
            conditions.append(PracticeKanjiORM.is_active.is_(active))
        return conditions

    def _select(self) -> Select[PracticeKanjiORM]:
        return select(PracticeKanjiORM).options(*_LOAD)
