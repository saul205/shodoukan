from datetime import UTC, datetime
from uuid import UUID

from shodoukan_practice.domain.entities import User

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_user_shape() -> None:
    user = User(
        id=UUID("8f14e45f-ceea-467a-9575-2ad4a6a1a001"),
        username="saul",
        created_at=NOW,
        updated_at=NOW,
    )
    assert User.model_validate(user.model_dump()) == user
