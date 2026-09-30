from collections.abc import Sequence

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from ...domain.entities import EntryCollection, PracticeEntry
from ...domain.exceptions import CollectionOwnershipError, EntityNotFoundError
from ...domain.repositories import EntryCollectionRepository
from ..db.mappers import entry_collection_to_db, entry_collection_to_domain
from ..db.orm import EntryCollectionORM, PracticeEntryORM, entry_collection_items


class SqlAlchemyEntryCollectionRepository(EntryCollectionRepository):
    """Flushes but never commits: the caller owns the transaction.

    Membership is read and written directly on `entry_collection_items`.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, collection_id: int, user_id: int) -> EntryCollection | None:
        row = self._get_row(collection_id, user_id)
        return entry_collection_to_domain(row) if row else None

    def list_for_user(self, user_id: int) -> list[EntryCollection]:
        query = (
            select(EntryCollectionORM)
            .where(EntryCollectionORM.user_id == user_id)
            .order_by(EntryCollectionORM.name)
        )
        return [entry_collection_to_domain(row) for row in self._session.scalars(query)]

    def list_for_item(self, entry: PracticeEntry) -> list[EntryCollection]:
        query = (
            select(EntryCollectionORM)
            .join(
                entry_collection_items,
                entry_collection_items.c.collection_id == EntryCollectionORM.id,
            )
            .where(
                entry_collection_items.c.entry_id == entry.id,
                EntryCollectionORM.user_id == entry.user_id,
            )
            .order_by(EntryCollectionORM.name)
        )
        return [entry_collection_to_domain(row) for row in self._session.scalars(query)]

    def add_item(self, collection: EntryCollection, entry: PracticeEntry) -> None:
        """Link `entry` to `collection`; a no-op if it's already linked."""
        if collection.user_id != entry.user_id:
            raise CollectionOwnershipError(
                "cannot add another user's item to a collection"
            )
        link = {"collection_id": collection.id, "entry_id": entry.id}
        exists = self._session.scalar(
            select(entry_collection_items.c.collection_id).filter_by(**link)
        )
        if exists is None:
            self._session.execute(insert(entry_collection_items).values(link))
            self._session.flush()

    def remove_item(self, collection: EntryCollection, entry: PracticeEntry) -> None:
        """Unlink `entry` from `collection`; a no-op if it isn't linked."""
        self._session.execute(
            delete(entry_collection_items).where(
                entry_collection_items.c.collection_id == collection.id,
                entry_collection_items.c.entry_id == entry.id,
            )
        )
        self._session.flush()

    def item_ids(self, collections: Sequence[EntryCollection]) -> set[int]:
        """Distinct ids of the active items across `collections`."""
        query = (
            select(entry_collection_items.c.entry_id)
            .join(
                PracticeEntryORM,
                PracticeEntryORM.id == entry_collection_items.c.entry_id,
            )
            .where(
                entry_collection_items.c.collection_id.in_([c.id for c in collections]),
                PracticeEntryORM.is_active.is_(True),
            )
            .distinct()
        )
        return set(self._session.scalars(query))

    def add(self, collection: EntryCollection) -> EntryCollection:
        row = entry_collection_to_db(collection)
        self._session.add(row)
        self._session.flush()
        return entry_collection_to_domain(row)

    def update(self, collection: EntryCollection) -> EntryCollection:
        self._require_row(collection)
        row = self._session.merge(entry_collection_to_db(collection))
        self._session.flush()
        return entry_collection_to_domain(row)

    def delete(self, collection: EntryCollection) -> None:
        """Delete the collection and its links; the items themselves stay."""
        self._session.delete(self._require_row(collection))
        self._session.flush()

    def _get_row(self, collection_id: int, user_id: int) -> EntryCollectionORM | None:
        query = select(EntryCollectionORM).where(
            EntryCollectionORM.id == collection_id,
            EntryCollectionORM.user_id == user_id,
        )
        return self._session.scalars(query).one_or_none()

    def _require_row(self, collection: EntryCollection) -> EntryCollectionORM:
        row = (
            self._get_row(collection.id, collection.user_id) if collection.id else None
        )
        if row is None:
            raise EntityNotFoundError(f"collection {collection.id} not found")
        return row
