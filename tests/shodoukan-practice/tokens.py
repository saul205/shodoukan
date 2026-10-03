"""Access tokens for API tests, signed with a key generated for the test run."""

from collections.abc import Callable

from factories import USER_ID

ISSUER = "https://keycloak.test/realms/shodoukan"

# Subject of the default test token: the `user` fixture's id.
DEFAULT_SUBJECT = str(USER_ID)

TokenFactory = Callable[..., str]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
