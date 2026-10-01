"""Access-token verification for an OAuth2 resource server (Keycloak).

The API doesn't log users in: the frontend gets an access token from
Keycloak and sends it as `Authorization: Bearer <token>`. Here the token's
RS256 signature is checked against the realm's public keys (JWKS), along with
expiry, issuer and, when configured, audience. The `sub` claim identifies the
user.

Configuration (environment):
- `AUTH_ISSUER`: the realm URL, e.g. `https://keycloak.example/realms/shodoukan`.
- `AUTH_AUDIENCE`: optional. Keycloak only puts a custom audience in access
  tokens when an audience mapper is configured; set it once that exists.
- `AUTH_JWKS_URL`: optional, defaults to the realm's
  `<issuer>/protocol/openid-connect/certs`.
"""

import os
from collections.abc import Callable
from typing import Any

import jwt

ALGORITHMS = ["RS256"]

# Given a raw token, return the public key that should have signed it.
KeyResolver = Callable[[str], Any]


class TokenVerifier:
    def __init__(
        self, issuer: str, audience: str | None, key_for_token: KeyResolver
    ) -> None:
        self._issuer = issuer
        self._audience = audience
        self._key_for_token = key_for_token

    @classmethod
    def from_env(cls) -> "TokenVerifier":
        issuer = os.environ.get("AUTH_ISSUER")
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

    def subject(self, token: str) -> str:
        """The verified token's `sub` claim.

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
        return str(claims["sub"])
