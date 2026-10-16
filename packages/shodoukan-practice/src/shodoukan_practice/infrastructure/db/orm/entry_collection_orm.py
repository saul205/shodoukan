"""Entry collections, their membership link table, and what sharing them
stores: the published snapshot and who downloaded it.

Membership has no ORM relationship on purpose: repositories read and change
it with explicit queries on `entry_collection_items`.
"""

import datetime
import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
    Uuid,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base_orm import (
    Base,
    UtcDateTime,
    created_at_column,
    updated_at_column,
)


class EntryCollectionORM(Base):
    __tablename__ = "entry_collections"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None]
    is_public: Mapped[bool] = mapped_column(default=False, server_default=false())
    published_version: Mapped[int] = mapped_column(default=0, server_default="0")
    published_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime)
    source_collection_id: Mapped[int | None]
    source_version: Mapped[int | None]
    created_at: Mapped[datetime.datetime] = created_at_column()
    updated_at: Mapped[datetime.datetime] = updated_at_column()


entry_collection_items = Table(
    "entry_collection_items",
    Base.metadata,
    Column(
        "collection_id",
        Integer,
        ForeignKey("entry_collections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "entry_id",
        Integer,
        ForeignKey("practice_entries.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,  # list_for_item: collections an item belongs to
    ),
    Column(
        "added_at",
        UtcDateTime,
        nullable=False,  # set by the repository (domain clock)
    ),
    # Put there by an import from the collection's source.
    Column(
        "from_source", Boolean, nullable=False, default=False, server_default=false()
    ),
)


class EntryCollectionPublicationORM(Base):
    """The published snapshot of a collection (its latest version only; the
    version number and date live on the collection)."""

    __tablename__ = "entry_collection_publications"

    collection_id: Mapped[int] = mapped_column(
        ForeignKey("entry_collections.id", ondelete="CASCADE"), primary_key=True
    )
    item_count: Mapped[int]
    includes_notes: Mapped[bool]
    # A `SharedEntryCollection`, as JSON.
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


entry_collection_dismissed_items = Table(
    "entry_collection_dismissed_items",
    Base.metadata,
    Column(
        "collection_id",
        Integer,
        ForeignKey("entry_collections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # The item's shared key (`shared_key`): what the user took out of a copy,
    # which updates from its source don't bring back.
    Column("item_key", String(64), primary_key=True),
)


entry_collection_downloads = Table(
    "entry_collection_downloads",
    Base.metadata,
    Column(
        "collection_id",
        Integer,
        ForeignKey("entry_collections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "user_id",
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
    Column("version", Integer, nullable=False),  # the latest one imported
    Column("downloaded_at", UtcDateTime, nullable=False),
)
