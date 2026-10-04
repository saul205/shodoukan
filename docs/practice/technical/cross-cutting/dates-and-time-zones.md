# Dates and Time Zones

[← Technical documentation](../README.md)

How dates are stored, handled and sent, and who decides "now".

## The rule

| Where | Form |
|---|---|
| Database | naive UTC (`timestamp without time zone`) |
| Backend (domain, use cases, repositories) | aware UTC `datetime` |
| API (planned) | ISO 8601 with offset, e.g. `2026-07-01T10:00:00Z`; clients convert to local time |

## `UtcDateTime` (`infrastructure/db/orm/base_orm.py`)

A SQLAlchemy `TypeDecorator` over `DateTime(timezone=False)`, used by every datetime
column:

- **write:** converts the aware value to UTC and drops the zone. Naive datetimes are
  rejected with `ValueError` instead of guessing their zone;
- **read:** attaches UTC to the naive value.

Both engines behave the same: SQLite has no time zones, and PostgreSQL stores the
naive value as is.

## Who decides "now"

The domain:

- `domain/clock.py` → `utc_now()` is the only source of "now";
- aggregates default `created_at` / `updated_at` through `TimestampedEntity` and bump
  `updated_at` with `touch()` (see
  [entities](../domain/entities.md#timestamps-and-touch));
- rows with no entity behind them (`added_at` on collection links) are stamped by the
  repository with `utc_now()`.

Timestamp columns have **no** ORM `default`, `onupdate` or database `server_default`,
so a missing timestamp fails instead of being invented by persistence.

Why no database defaults: [decisions](../decisions.md#the-domain-decides-now-no-database-defaults-for-timestamps).

## The user's time zone

Dates stay UTC everywhere except where a figure depends on the user's day: the answers
per day of `GET /statistics`. The client sends its IANA zone (`tz`, default `UTC`;
unknown → `422`), and `GetPracticeStatistics` buckets the UTC `answered_at` values by
their local date with `zoneinfo`, in Python so SQLite and PostgreSQL agree. Why:
[decisions](../decisions.md#activity-per-day-is-grouped-in-python).
