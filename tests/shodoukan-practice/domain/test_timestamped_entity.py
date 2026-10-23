from datetime import UTC, datetime

from shodoukan_practice.domain.entities import TimestampedEntity

PAST = datetime(2026, 1, 1, tzinfo=UTC)


def test_timestamps_default_to_now_in_utc() -> None:
    before = datetime.now(UTC)
    entity = TimestampedEntity()

    assert entity.created_at.tzinfo == UTC
    assert before <= entity.created_at <= datetime.now(UTC)
    assert entity.updated_at.tzinfo == UTC


def test_touch_moves_updated_at_and_keeps_created_at() -> None:
    entity = TimestampedEntity(created_at=PAST, updated_at=PAST)
    entity.touch()

    assert entity.created_at == PAST
    assert entity.updated_at > PAST
