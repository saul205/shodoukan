"""Port for persisting practice users."""

from typing import Protocol

from ..entities import User


class UserRepository(Protocol):
    def get(self, user_id: int) -> User | None: ...

    def get_by_subject(self, subject: str) -> User | None:
        """The user with this identity-provider id (token `sub`), if registered."""
        ...

    def add(self, user: User) -> User: ...
