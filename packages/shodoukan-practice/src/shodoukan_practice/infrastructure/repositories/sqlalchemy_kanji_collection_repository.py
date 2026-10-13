from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from sqlalchemy import Select, delete, func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from ...domain.clock import utc_now
from ...domain.entities import KanjiCollection, PracticeKanji, SharedKanjiCollection
from ...domain.exceptions import (
    CollectionNameTakenError,
    CollectionOwnershipError,
    EntityNotFoundError,
)
from ...domain.repositories import KanjiCollectionRepository
from ...domain.searches import PublicCollectionSearch, PublicCollectionSummary
from ..db.mappers import kanji_collection_to_db, kanji_collection_to_domain
from ..db.orm import (
    KanjiCollectionORM,
    KanjiCollectionPublicationORM,
    PracticeKanjiORM,
    UserORM,
    kanji_collection_dismissed_items,
    kanji_collection_downloads,
    kanji_collection_items,
)


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

    def add_item(
        self,
        collection: KanjiCollection,
        kanji: PracticeKanji,
        from_source: bool = False,
    ) -> None:
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
                insert(kanji_collection_items).values(
                    **link, added_at=utc_now(), from_source=from_source
                )
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
        """Raises `CollectionNameTakenError` if the user has that name already."""
        row = kanji_collection_to_db(collection)
        with self._name_guard(collection):
            self._session.add(row)
        return kanji_collection_to_domain(row)

    def update(self, collection: KanjiCollection) -> KanjiCollection:
        """Raises `CollectionNameTakenError` if the user has that name already."""
        self._require_row(collection)
        with self._name_guard(collection):
            row = self._session.merge(kanji_collection_to_db(collection))
        return kanji_collection_to_domain(row)

    def delete(self, collection: KanjiCollection) -> None:
        """Delete the collection and its links; the items themselves stay."""
        self._session.delete(self._require_row(collection))
        self._session.flush()

    # --- Sharing ---

    def save_publication(
        self,
        collection: KanjiCollection,
        shared: SharedKanjiCollection,
        includes_notes: bool,
    ) -> None:
        self._require_row(collection)
        self._session.merge(
            KanjiCollectionPublicationORM(
                collection_id=collection.id,
                item_count=len(shared.items),
                includes_notes=includes_notes,
                payload=shared.model_dump(mode="json"),
            )
        )
        self._session.flush()

    def get_publication(
        self, collection: KanjiCollection
    ) -> SharedKanjiCollection | None:
        row = self._session.get(KanjiCollectionPublicationORM, collection.id)
        return SharedKanjiCollection.model_validate(row.payload) if row else None

    def get_public(self, collection_id: int) -> KanjiCollection | None:
        query = select(KanjiCollectionORM).where(
            KanjiCollectionORM.id == collection_id,
            KanjiCollectionORM.is_public.is_(True),
        )
        row = self._session.scalars(query).one_or_none()
        return kanji_collection_to_domain(row) if row else None

    def find_public(
        self,
        search: PublicCollectionSearch,
        viewer_id: UUID,
        limit: int,
        offset: int,
    ) -> list[PublicCollectionSummary[KanjiCollection]]:
        query = self._public(viewer_id)
        query = query.where(*self._public_filters(search, viewer_id))
        query = query.order_by(*self._public_order(search))
        rows = self._session.execute(query.limit(limit).offset(offset)).all()
        return [self._summary(*row) for row in rows]

    def count_public(self, search: PublicCollectionSearch, viewer_id: UUID) -> int:
        query = (
            select(func.count())
            .select_from(KanjiCollectionORM)
            .join(UserORM, UserORM.id == KanjiCollectionORM.user_id)
            .join(
                KanjiCollectionPublicationORM,
                KanjiCollectionPublicationORM.collection_id == KanjiCollectionORM.id,
            )
            .where(*self._public_filters(search, viewer_id))
        )
        return self._session.scalar(query) or 0

    def public_summary(
        self, collection: KanjiCollection, viewer_id: UUID
    ) -> PublicCollectionSummary[KanjiCollection]:
        query = self._public(viewer_id).where(KanjiCollectionORM.id == collection.id)
        return self._summary(*self._session.execute(query).one())

    def record_download(
        self, collection: KanjiCollection, user_id: UUID, version: int
    ) -> None:
        where = (
            kanji_collection_downloads.c.collection_id == collection.id,
            kanji_collection_downloads.c.user_id == user_id,
        )
        latest = {"version": version, "downloaded_at": utc_now()}
        known = self._session.scalar(
            select(kanji_collection_downloads.c.version).where(*where)
        )
        if known is None:
            try:
                # Savepoint: a concurrent first import by the same user
                # (primary-key clash) rolls back only this insert.
                with self._session.begin_nested():
                    self._session.execute(
                        insert(kanji_collection_downloads).values(
                            collection_id=collection.id, user_id=user_id, **latest
                        )
                    )
                return
            except IntegrityError:
                pass
        self._session.execute(
            update(kanji_collection_downloads).where(*where).values(**latest)
        )
        self._session.flush()

    def _public(self, viewer_id: UUID) -> Select[Any]:
        """Public collections with their owner, item count, downloads (not
        the owner's) and the version the viewer imported."""
        viewer_version = (
            select(kanji_collection_downloads.c.version)
            .where(
                kanji_collection_downloads.c.collection_id == KanjiCollectionORM.id,
                kanji_collection_downloads.c.user_id == viewer_id,
            )
            .scalar_subquery()
        )
        return (
            select(
                KanjiCollectionORM,
                UserORM.username,
                KanjiCollectionPublicationORM.item_count,
                self._downloads().label("downloads"),
                viewer_version.label("viewer_version"),
            )
            .join(UserORM, UserORM.id == KanjiCollectionORM.user_id)
            .join(
                KanjiCollectionPublicationORM,
                KanjiCollectionPublicationORM.collection_id == KanjiCollectionORM.id,
            )
            .where(KanjiCollectionORM.is_public.is_(True))
        )

    @staticmethod
    def _public_filters(search: PublicCollectionSearch, viewer_id: UUID) -> list[Any]:
        conditions: list[Any] = [KanjiCollectionORM.is_public.is_(True)]
        if search.owner == "mine":
            conditions.append(KanjiCollectionORM.user_id == viewer_id)
        elif search.owner == "others":
            conditions.append(KanjiCollectionORM.user_id != viewer_id)
        if search.text:
            text = search.text
            conditions.append(
                or_(
                    func.lower(KanjiCollectionORM.name).contains(text, autoescape=True),
                    func.lower(
                        func.coalesce(KanjiCollectionORM.description, "")
                    ).contains(text, autoescape=True),
                    func.lower(UserORM.username).contains(text, autoescape=True),
                )
            )
        return conditions

    @classmethod
    def _public_order(cls, search: PublicCollectionSearch) -> list[Any]:
        recent = [KanjiCollectionORM.published_at.desc(), KanjiCollectionORM.id.desc()]
        if search.sort == "recent":
            return recent
        return [cls._downloads().desc(), *recent]

    @staticmethod
    def _downloads() -> Any:
        """How many users other than the owner imported the collection."""
        return (
            select(func.count())
            .where(
                kanji_collection_downloads.c.collection_id == KanjiCollectionORM.id,
                kanji_collection_downloads.c.user_id != KanjiCollectionORM.user_id,
            )
            .scalar_subquery()
        )

    @staticmethod
    def _summary(
        row: KanjiCollectionORM,
        username: str,
        item_count: int,
        downloads: int,
        viewer_version: int | None,
    ) -> PublicCollectionSummary[KanjiCollection]:
        return PublicCollectionSummary(
            collection=kanji_collection_to_domain(row),
            owner_username=username,
            item_count=item_count,
            downloads=downloads,
            viewer_version=viewer_version,
        )

    # --- Following a source ---

    def is_from_source(self, collection: KanjiCollection, kanji: PracticeKanji) -> bool:
        query = select(kanji_collection_items.c.from_source).where(
            kanji_collection_items.c.collection_id == collection.id,
            kanji_collection_items.c.kanji_id == kanji.id,
        )
        return bool(self._session.scalar(query))

    def source_item_ids(self, collection: KanjiCollection) -> set[int]:
        query = select(kanji_collection_items.c.kanji_id).where(
            kanji_collection_items.c.collection_id == collection.id,
            kanji_collection_items.c.from_source.is_(True),
        )
        return set(self._session.scalars(query))

    def dismiss_item(self, collection: KanjiCollection, key: str) -> None:
        dismissed = kanji_collection_dismissed_items
        row = {"collection_id": collection.id, "item_key": key}
        known = self._session.scalar(select(dismissed.c.item_key).filter_by(**row))
        if known is None:
            self._session.execute(insert(dismissed).values(**row))
            self._session.flush()

    def undismiss_item(self, collection: KanjiCollection, key: str) -> bool:
        dismissed = kanji_collection_dismissed_items
        row = {"collection_id": collection.id, "item_key": key}
        known = self._session.scalar(select(dismissed.c.item_key).filter_by(**row))
        if known is None:
            return False
        self._session.execute(delete(dismissed).filter_by(**row))
        self._session.flush()
        return True

    def dismissed_items(self, collection: KanjiCollection) -> set[str]:
        dismissed = kanji_collection_dismissed_items
        query = select(dismissed.c.item_key).where(
            dismissed.c.collection_id == collection.id
        )
        return set(self._session.scalars(query))

    def latest_source_versions(self, user_id: UUID) -> dict[int, int]:
        source = aliased(KanjiCollectionORM)
        query = (
            select(KanjiCollectionORM.id, source.published_version)
            .join(source, source.id == KanjiCollectionORM.source_collection_id)
            .where(KanjiCollectionORM.user_id == user_id, source.is_public.is_(True))
        )
        return dict(self._session.execute(query).all())

    @contextmanager
    def _name_guard(self, collection: KanjiCollection) -> Iterator[None]:
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

    def _name_taken(self, collection: KanjiCollection) -> bool:
        query = select(KanjiCollectionORM.id).where(
            KanjiCollectionORM.user_id == collection.user_id,
            KanjiCollectionORM.name == collection.name,
        )
        if collection.id is not None:
            query = query.where(KanjiCollectionORM.id != collection.id)
        return self._session.scalar(query) is not None

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
