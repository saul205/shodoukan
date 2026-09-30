"""Port for persisting practice users."""

from typing import Protocol

from ..entities import User


class UserRepository(Protocol):
    def get(self, user_id: int) -> User | None: ...

    def add(self, user: User) -> User: ...
