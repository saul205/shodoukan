"""Use cases about practice users."""

from uuid import UUID

from ...domain.entities import User
from ...domain.repositories import UserRepository


class EnsureUser:
    """The practice user behind an authenticated identity, created on first use.

    The identity provider decides who can sign up, so any identity it vouches
    for gets a practice user the first time it calls the API. Its display name
    follows the provider's: a rename there is taken on the next request. A
    token without one keeps the stored name (a new user is named by its id).
    Doesn't commit.
    """

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def execute(self, user_id: UUID, username: str | None) -> User:
        """`user_id` is the identity provider's user id (token `sub`)."""
        existing = self._users.get(user_id)
        if existing is not None:
            if username is None or existing.username == username:
                return existing
            existing.rename(username)
            return self._users.update(existing)
        user, _ = self._users.add_if_absent(
            User(id=user_id, username=username or str(user_id))
        )
        return user
