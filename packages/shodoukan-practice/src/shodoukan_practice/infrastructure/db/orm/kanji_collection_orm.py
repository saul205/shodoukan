"""Kanji collections and their membership link table.

Membership has no ORM relationship on purpose: repositories read and change
it with explicit queries on `kanji_collection_items`.
"""

import datetime

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base_orm import (
    Base,
    UtcDateTime,
    created_at_column,
    updated_at_column,
)


class KanjiCollectionORM(Base):
    __tablename__ = "kanji_collections"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None]
    created_at: Mapped[datetime.datetime] = created_at_column()
    updated_at: Mapped[datetime.datetime] = updated_at_column()


kanji_collection_items = Table(
    "kanji_collection_items",
    Base.metadata,
    Column(
        "collection_id",
        Integer,
        ForeignKey("kanji_collections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "kanji_id",
        Integer,
        ForeignKey("practice_kanji.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,  # list_for_item: collections an item belongs to
    ),
    Column(
        "added_at",
        UtcDateTime,
        nullable=False,  # set by the repository (domain clock)
    ),
)
