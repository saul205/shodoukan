from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from ...domain.clock import utc_now
from ...domain.entities import KanjiCollection, PracticeKanji
from ...domain.exceptions import CollectionOwnershipError, EntityNotFoundError
from ...domain.repositories import KanjiCollectionRepository
from ..db.mappers import kanji_collection_to_db, kanji_collection_to_domain
from ..db.orm import KanjiCollectionORM, PracticeKanjiORM, kanji_collection_items


class SqlAlchemyKanjiCollectionRepository(KanjiCollectionRepository):
    """Flushes but never commits: the caller owns the transaction.

    Membership is read and written directly on `kanji_collection_items`.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, collection_id: int, user_id: UUID) -> KanjiCollection | None:
        row = self._get_row(collection_id, user_id)
        return kanji_collection_to_domain(row) if row else None

    def list_for_user(self, user_id: UUID) -> list[KanjiCollection]:
        query = (
            select(KanjiCollectionORM)
            .where(KanjiCollectionORM.user_id == user_id)
            .order_by(KanjiCollectionORM.name)
        )
        return [kanji_collection_to_domain(row) for row in self._session.scalars(query)]

    def list_for_item(self, kanji: PracticeKanji) -> list[KanjiCollection]:
        query = (
            select(KanjiCollectionORM)
            .join(
                kanji_collection_items,
                kanji_collection_items.c.collection_id == KanjiCollectionORM.id,
            )
            .where(
                kanji_collection_items.c.kanji_id == kanji.id,
                KanjiCollectionORM.user_id == kanji.user_id,
            )
            .order_by(KanjiCollectionORM.name)
        )
        return [kanji_collection_to_domain(row) for row in self._session.scalars(query)]

    def add_item(self, collection: KanjiCollection, kanji: PracticeKanji) -> None:
        """Link `kanji` to `collection`; a no-op if it's already linked."""
        if collection.user_id != kanji.user_id:
            raise CollectionOwnershipError(
                "cannot add another user's item to a collection"
            )
        link = {"collection_id": collection.id, "kanji_id": kanji.id}
        exists = self._session.scalar(
            select(kanji_collection_items.c.collection_id).filter_by(**link)
        )
        if exists is None:
            self._session.execute(
                insert(kanji_collection_items).values(**link, added_at=utc_now())
            )
            self._session.flush()

    def remove_item(self, collection: KanjiCollection, kanji: PracticeKanji) -> None:
        """Unlink `kanji` from `collection`; a no-op if it isn't linked."""
        self._session.execute(
            delete(kanji_collection_items).where(
                kanji_collection_items.c.collection_id == collection.id,
                kanji_collection_items.c.kanji_id == kanji.id,
            )
        )
        self._session.flush()

    def item_ids(self, collections: Sequence[KanjiCollection]) -> set[int]:
        """Distinct ids of the active items across `collections`."""
        query = (
            select(kanji_collection_items.c.kanji_id)
            .join(
                PracticeKanjiORM,
                PracticeKanjiORM.id == kanji_collection_items.c.kanji_id,
            )
            .where(
                kanji_collection_items.c.collection_id.in_([c.id for c in collections]),
                PracticeKanjiORM.is_active.is_(True),
            )
            .distinct()
        )
        return set(self._session.scalars(query))

    def add(self, collection: KanjiCollection) -> KanjiCollection:
        row = kanji_collection_to_db(collection)
        self._session.add(row)
        self._session.flush()
        return kanji_collection_to_domain(row)

    def update(self, collection: KanjiCollection) -> KanjiCollection:
        self._require_row(collection)
        row = self._session.merge(kanji_collection_to_db(collection))
        self._session.flush()
        return kanji_collection_to_domain(row)

    def delete(self, collection: KanjiCollection) -> None:
        """Delete the collection and its links; the items themselves stay."""
        self._session.delete(self._require_row(collection))
        self._session.flush()

    def _get_row(self, collection_id: int, user_id: UUID) -> KanjiCollectionORM | None:
        query = select(KanjiCollectionORM).where(
            KanjiCollectionORM.id == collection_id,
            KanjiCollectionORM.user_id == user_id,
        )
        return self._session.scalars(query).one_or_none()

    def _require_row(self, collection: KanjiCollection) -> KanjiCollectionORM:
        row = (
            self._get_row(collection.id, collection.user_id) if collection.id else None
        )
        if row is None:
            raise EntityNotFoundError(f"collection {collection.id} not found")
        return row
