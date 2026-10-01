from datetime import UTC, datetime

from shodoukan_practice.domain.entities import User

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_user_shape() -> None:
    user = User(
        id=1, subject="sub-saul", username="saul", created_at=NOW, updated_at=NOW
    )
    assert User.model_validate(user.model_dump()) == user
