"""Access-token verification for an OAuth2 resource server (Keycloak).

The API doesn't log users in: the frontend (or the Swagger UI) signs the user
in with Keycloak and sends the access token as `Authorization: Bearer <token>`.
Here the token's RS256 signature is checked against the realm's public keys
(JWKS), along with expiry, issuer and, when configured, audience. The `sub`
claim identifies the user; `preferred_username` gives a display name.

Configuration (environment):
- `AUTH_ISSUER`: the realm URL, e.g. `https://keycloak.example/realms/shodoukan`.
- `AUTH_AUDIENCE`: optional but recommended. The local realm adds
  `shodoukan-practice` to `aud` through an audience mapper on its clients.
- `AUTH_JWKS_URL`: optional, defaults to the realm's
  `<issuer>/protocol/openid-connect/certs`.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import jwt

ALGORITHMS = ["RS256"]

# Given a raw token, return the public key that should have signed it.
KeyResolver = Callable[[str], Any]


DEFAULT_ISSUER = "http://localhost:8080/realms/shodoukan"


def issuer_from_env() -> str | None:
    return os.environ.get("AUTH_ISSUER") or None


def authorization_url(issuer: str) -> str:
    return f"{issuer.rstrip('/')}/protocol/openid-connect/auth"


def token_url(issuer: str) -> str:
    return f"{issuer.rstrip('/')}/protocol/openid-connect/token"


@dataclass(frozen=True)
class TokenIdentity:
    """Who a verified token belongs to."""

    user_id: UUID  # the token's `sub`
    username: str


class TokenVerifier:
    def __init__(
        self, issuer: str, audience: str | None, key_for_token: KeyResolver
    ) -> None:
        self._issuer = issuer
        self._audience = audience
        self._key_for_token = key_for_token

    @classmethod
    def from_env(cls) -> "TokenVerifier":
        issuer = issuer_from_env()
        if not issuer:
            raise RuntimeError("AUTH_ISSUER is not set; see .env.example")
        jwks_url = os.environ.get("AUTH_JWKS_URL") or (
            f"{issuer.rstrip('/')}/protocol/openid-connect/certs"
        )
        # PyJWKClient caches the key set and refetches on an unknown key id.
        jwks = jwt.PyJWKClient(jwks_url)
        return cls(
            issuer=issuer,
            audience=os.environ.get("AUTH_AUDIENCE") or None,
            key_for_token=lambda token: jwks.get_signing_key_from_jwt(token).key,
        )

    def identity(self, token: str) -> TokenIdentity:
        """The verified token's `sub` (a UUID) and `preferred_username`.

        `preferred_username` falls back to `sub`. Practice users are keyed by
        the provider's user id, so a `sub` that isn't a UUID is rejected.

        Raises `jwt.PyJWTError` if the token is malformed, expired, signed by
        an unknown key, or issued for another issuer or audience.
        """
        claims = jwt.decode(
            token,
            self._key_for_token(token),
            algorithms=ALGORITHMS,
            issuer=self._issuer,
            audience=self._audience,
            options={
                "require": ["exp", "iss", "sub"],
                "verify_aud": self._audience is not None,
            },
        )
        subject = str(claims["sub"])
        try:
            user_id = UUID(subject)
        except ValueError as error:
            raise jwt.InvalidTokenError("the `sub` claim is not a UUID") from error
        return TokenIdentity(
            user_id=user_id,
            username=str(claims.get("preferred_username") or subject),
        )
