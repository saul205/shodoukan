"""Port for persisting practice users."""

from typing import Protocol
from uuid import UUID

from ..entities import User


class UserRepository(Protocol):
    def get(self, user_id: UUID) -> User | None: ...

    def lock(self, user_id: UUID) -> None:
        """Lock the user until the transaction ends, to serialize changes that
        span several of their rows (e.g. their one open exercise session)."""
        ...

    def add(self, user: User) -> User: ...

    def add_if_absent(self, user: User) -> tuple[User, bool]:
        """Store `user` unless one with the same id exists.

        Returns the stored user and whether it was created. Safe against two
        concurrent first requests from the same identity.
        """
        ...
