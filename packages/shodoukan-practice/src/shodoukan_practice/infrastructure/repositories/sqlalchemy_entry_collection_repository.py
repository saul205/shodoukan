from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...domain.clock import utc_now
from ...domain.entities import EntryCollection, PracticeEntry
from ...domain.exceptions import (
    CollectionNameTakenError,
    CollectionOwnershipError,
    EntityNotFoundError,
)
from ...domain.repositories import EntryCollectionRepository
from ..db.mappers import entry_collection_to_db, entry_collection_to_domain
from ..db.orm import EntryCollectionORM, PracticeEntryORM, entry_collection_items


class SqlAlchemyEntryCollectionRepository(EntryCollectionRepository):
    """Flushes but never commits: the caller owns the transaction.

    Membership is read and written directly on `entry_collection_items`.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, collection_id: int, user_id: UUID) -> EntryCollection | None:
        row = self._get_row(collection_id, user_id)
        return entry_collection_to_domain(row) if row else None

    def list_for_user(self, user_id: UUID) -> list[EntryCollection]:
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
            self._session.execute(
                insert(entry_collection_items).values(**link, added_at=utc_now())
            )
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
        """Raises `CollectionNameTakenError` if the user has that name already."""
        row = entry_collection_to_db(collection)
        with self._name_guard(collection):
            self._session.add(row)
        return entry_collection_to_domain(row)

    def update(self, collection: EntryCollection) -> EntryCollection:
        """Raises `CollectionNameTakenError` if the user has that name already."""
        self._require_row(collection)
        with self._name_guard(collection):
            row = self._session.merge(entry_collection_to_db(collection))
        return entry_collection_to_domain(row)

    def delete(self, collection: EntryCollection) -> None:
        """Delete the collection and its links; the items themselves stay."""
        self._session.delete(self._require_row(collection))
        self._session.flush()

    @contextmanager
    def _name_guard(self, collection: EntryCollection) -> Iterator[None]:
        """Flush the block's changes in a savepoint; a name clash raises
        `CollectionNameTakenError` and rolls back only this block.

        The `(user_id, name)` unique constraint is the check, so a concurrent
        request taking the same name is caught too.
        """
        try:
            with self._session.begin_nested():
                yield
        except IntegrityError:
            if not self._name_taken(collection):
                raise
            raise CollectionNameTakenError(
                f"a collection named {collection.name!r} already exists"
            ) from None

    def _name_taken(self, collection: EntryCollection) -> bool:
        query = select(EntryCollectionORM.id).where(
            EntryCollectionORM.user_id == collection.user_id,
            EntryCollectionORM.name == collection.name,
        )
        if collection.id is not None:
            query = query.where(EntryCollectionORM.id != collection.id)
        return self._session.scalar(query) is not None

    def _get_row(self, collection_id: int, user_id: UUID) -> EntryCollectionORM | None:
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
