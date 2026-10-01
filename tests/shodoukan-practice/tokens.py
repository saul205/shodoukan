"""Access tokens for API tests, signed with a key generated for the test run."""

from collections.abc import Callable

ISSUER = "https://keycloak.test/realms/shodoukan"

TokenFactory = Callable[..., str]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
