"""Declarative base shared by every practice ORM model.

The naming convention gives every index and constraint a deterministic
name, so Alembic can generate and later drop/alter them reliably.
"""

import datetime
from typing import Any

from sqlalchemy import DateTime, Dialect, MetaData, TypeDecorator, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Relationship,
    mapped_column,
    relationship,
)

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Values allowed in `origin` columns, mirroring the domain's Literal.
ORIGINS = ("imported", "added")


class UtcDateTime(TypeDecorator[datetime.datetime]):
    """Timezone-aware datetime, always stored and returned in UTC.

    PostgreSQL keeps the offset (timestamptz) but SQLite doesn't and returns
    naive values; this makes both engines hand back the same aware datetime.
    Naive datetimes are rejected on write instead of guessing their zone.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime.datetime | None, dialect: Dialect
    ) -> datetime.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime; pass a timezone-aware value")
        return value.astimezone(datetime.UTC)

    def process_result_value(
        self, value: datetime.datetime | None, dialect: Dialect
    ) -> datetime.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.UTC)
        return value.astimezone(datetime.UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def created_at_column() -> Mapped[datetime.datetime]:
    return mapped_column(UtcDateTime, server_default=func.current_timestamp())


def updated_at_column() -> Mapped[datetime.datetime]:
    return mapped_column(
        UtcDateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


def children(order_by: str) -> Relationship[Any]:
    """One-to-many to rows owned by the parent: ordered, deleted with it."""
    return relationship(
        order_by=order_by, cascade="all, delete-orphan", passive_deletes=True
    )


def in_check(column: str, values: tuple[str, ...]) -> str:
    """SQL for a CHECK constraint restricting `column` to `values`."""
    allowed = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({allowed})"
