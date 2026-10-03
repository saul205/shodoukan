"""The domain's notion of "now": always a timezone-aware UTC datetime."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)
