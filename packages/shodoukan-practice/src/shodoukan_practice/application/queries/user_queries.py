"""Read use cases about practice users."""

from ...domain.entities import User
from ...domain.exceptions import UserNotRegisteredError
from ...domain.repositories import UserRepository


class GetRegisteredUser:
    """The practice user behind an authenticated identity.

    Users aren't created on first sight: an identity without a registered
    user is rejected until a registration use case exists.
    """

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def execute(self, subject: str) -> User:
        user = self._users.get_by_subject(subject)
        if user is None:
            raise UserNotRegisteredError(f"no practice user for subject {subject!r}")
        return user
