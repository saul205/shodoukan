from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from sqlalchemy import Select, delete, func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...domain.clock import utc_now
from ...domain.entities import EntryCollection, PracticeEntry, SharedEntryCollection
from ...domain.exceptions import (
    CollectionNameTakenError,
    CollectionOwnershipError,
    EntityNotFoundError,
)
from ...domain.repositories import EntryCollectionRepository
from ...domain.searches import PublicCollectionSearch, PublicCollectionSummary
from ..db.mappers import entry_collection_to_db, entry_collection_to_domain
from ..db.orm import (
    EntryCollectionORM,
    EntryCollectionPublicationORM,
    PracticeEntryORM,
    UserORM,
    entry_collection_downloads,
    entry_collection_items,
)


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

    def add_item(
        self,
        collection: EntryCollection,
        entry: PracticeEntry,
        from_source: bool = False,
    ) -> None:
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
                insert(entry_collection_items).values(
                    **link, added_at=utc_now(), from_source=from_source
                )
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

    # --- Sharing ---

    def save_publication(
        self,
        collection: EntryCollection,
        shared: SharedEntryCollection,
        includes_notes: bool,
    ) -> None:
        self._require_row(collection)
        self._session.merge(
            EntryCollectionPublicationORM(
                collection_id=collection.id,
                item_count=len(shared.items),
                includes_notes=includes_notes,
                payload=shared.model_dump(mode="json"),
            )
        )
        self._session.flush()

    def get_publication(
        self, collection: EntryCollection
    ) -> SharedEntryCollection | None:
        row = self._session.get(EntryCollectionPublicationORM, collection.id)
        return SharedEntryCollection.model_validate(row.payload) if row else None

    def get_public(self, collection_id: int) -> EntryCollection | None:
        query = select(EntryCollectionORM).where(
            EntryCollectionORM.id == collection_id,
            EntryCollectionORM.is_public.is_(True),
        )
        row = self._session.scalars(query).one_or_none()
        return entry_collection_to_domain(row) if row else None

    def find_public(
        self,
        search: PublicCollectionSearch,
        viewer_id: UUID,
        limit: int,
        offset: int,
    ) -> list[PublicCollectionSummary[EntryCollection]]:
        query = self._public(viewer_id)
        query = query.where(*self._public_filters(search, viewer_id))
        query = query.order_by(*self._public_order(search))
        rows = self._session.execute(query.limit(limit).offset(offset)).all()
        return [self._summary(*row) for row in rows]

    def count_public(self, search: PublicCollectionSearch, viewer_id: UUID) -> int:
        query = (
            select(func.count())
            .select_from(EntryCollectionORM)
            .join(UserORM, UserORM.id == EntryCollectionORM.user_id)
            .join(
                EntryCollectionPublicationORM,
                EntryCollectionPublicationORM.collection_id == EntryCollectionORM.id,
            )
            .where(*self._public_filters(search, viewer_id))
        )
        return self._session.scalar(query) or 0

    def public_summary(
        self, collection: EntryCollection, viewer_id: UUID
    ) -> PublicCollectionSummary[EntryCollection]:
        query = self._public(viewer_id).where(EntryCollectionORM.id == collection.id)
        return self._summary(*self._session.execute(query).one())

    def record_download(
        self, collection: EntryCollection, user_id: UUID, version: int
    ) -> None:
        where = (
            entry_collection_downloads.c.collection_id == collection.id,
            entry_collection_downloads.c.user_id == user_id,
        )
        latest = {"version": version, "downloaded_at": utc_now()}
        known = self._session.scalar(
            select(entry_collection_downloads.c.version).where(*where)
        )
        if known is None:
            try:
                # Savepoint: a concurrent first import by the same user
                # (primary-key clash) rolls back only this insert.
                with self._session.begin_nested():
                    self._session.execute(
                        insert(entry_collection_downloads).values(
                            collection_id=collection.id, user_id=user_id, **latest
                        )
                    )
                return
            except IntegrityError:
                pass
        self._session.execute(
            update(entry_collection_downloads).where(*where).values(**latest)
        )
        self._session.flush()

    def _public(self, viewer_id: UUID) -> Select[Any]:
        """Public collections with their owner, item count, downloads (not
        the owner's) and the version the viewer imported."""
        viewer_version = (
            select(entry_collection_downloads.c.version)
            .where(
                entry_collection_downloads.c.collection_id == EntryCollectionORM.id,
                entry_collection_downloads.c.user_id == viewer_id,
            )
            .scalar_subquery()
        )
        return (
            select(
                EntryCollectionORM,
                UserORM.username,
                EntryCollectionPublicationORM.item_count,
                self._downloads().label("downloads"),
                viewer_version.label("viewer_version"),
            )
            .join(UserORM, UserORM.id == EntryCollectionORM.user_id)
            .join(
                EntryCollectionPublicationORM,
                EntryCollectionPublicationORM.collection_id == EntryCollectionORM.id,
            )
            .where(EntryCollectionORM.is_public.is_(True))
        )

    @staticmethod
    def _public_filters(search: PublicCollectionSearch, viewer_id: UUID) -> list[Any]:
        conditions: list[Any] = [EntryCollectionORM.is_public.is_(True)]
        if search.owner == "mine":
            conditions.append(EntryCollectionORM.user_id == viewer_id)
        elif search.owner == "others":
            conditions.append(EntryCollectionORM.user_id != viewer_id)
        if search.text:
            text = search.text
            conditions.append(
                or_(
                    func.lower(EntryCollectionORM.name).contains(text, autoescape=True),
                    func.lower(
                        func.coalesce(EntryCollectionORM.description, "")
                    ).contains(text, autoescape=True),
                    func.lower(UserORM.username).contains(text, autoescape=True),
                )
            )
        return conditions

    @classmethod
    def _public_order(cls, search: PublicCollectionSearch) -> list[Any]:
        recent = [EntryCollectionORM.published_at.desc(), EntryCollectionORM.id.desc()]
        if search.sort == "recent":
            return recent
        return [cls._downloads().desc(), *recent]

    @staticmethod
    def _downloads() -> Any:
        """How many users other than the owner imported the collection."""
        return (
            select(func.count())
            .where(
                entry_collection_downloads.c.collection_id == EntryCollectionORM.id,
                entry_collection_downloads.c.user_id != EntryCollectionORM.user_id,
            )
            .scalar_subquery()
        )

    @staticmethod
    def _summary(
        row: EntryCollectionORM,
        username: str,
        item_count: int,
        downloads: int,
        viewer_version: int | None,
    ) -> PublicCollectionSummary[EntryCollection]:
        return PublicCollectionSummary(
            collection=entry_collection_to_domain(row),
            owner_username=username,
            item_count=item_count,
            downloads=downloads,
            viewer_version=viewer_version,
        )

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
