"""Entry collections and their membership link table.

Membership has no ORM relationship on purpose: repositories read and change
it with explicit queries on `entry_collection_items`.
"""

import datetime

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base_orm import Base, UtcDateTime, created_at_column, updated_at_column


class EntryCollectionORM(Base):
    __tablename__ = "entry_collections"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None]
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
        nullable=False,
        server_default=func.current_timestamp(),
    ),
)
