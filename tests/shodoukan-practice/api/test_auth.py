from datetime import timedelta
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from factories import USER_ID
from tokens import ISSUER, TokenFactory

from shodoukan_practice.api.auth import TokenVerifier

PROVIDER_ID = UUID("0b6f3c2e-5d4a-4e2b-9a1f-3c5d7e9f1a2b")


def test_valid_token_gives_its_identity(
    verifier: TokenVerifier, make_token: TokenFactory
) -> None:
    identity = verifier.identity(make_token(str(PROVIDER_ID), preferred_username="k"))

    assert identity.user_id == PROVIDER_ID
    assert identity.username == "k"


def test_username_falls_back_to_the_subject(
    verifier: TokenVerifier, make_token: TokenFactory
) -> None:
    identity = verifier.identity(make_token(str(PROVIDER_ID)))
    assert identity.username == str(PROVIDER_ID)


def test_subject_must_be_a_uuid(
    verifier: TokenVerifier, make_token: TokenFactory
) -> None:
    with pytest.raises(jwt.InvalidTokenError, match="UUID"):
        verifier.identity(make_token("auth0|abc123"))


def test_expired_token_is_rejected(
    verifier: TokenVerifier, make_token: TokenFactory
) -> None:
    with pytest.raises(jwt.ExpiredSignatureError):
        verifier.identity(make_token(expires_in=timedelta(minutes=-1)))


def test_other_issuer_is_rejected(
    verifier: TokenVerifier, make_token: TokenFactory
) -> None:
    with pytest.raises(jwt.InvalidIssuerError):
        verifier.identity(make_token(issuer="https://evil.test/realms/x"))


def test_token_signed_by_another_key_is_rejected(
    verifier: TokenVerifier, make_token: TokenFactory
) -> None:
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(jwt.InvalidSignatureError):
        verifier.identity(make_token(key=other_key))


def test_audience_is_checked_when_configured(
    signing_key: rsa.RSAPrivateKey, make_token: TokenFactory
) -> None:
    public_key = signing_key.public_key()
    verifier = TokenVerifier(ISSUER, "shodoukan-practice", lambda _: public_key)

    identity = verifier.identity(make_token(aud="shodoukan-practice"))
    assert identity.user_id == USER_ID
    with pytest.raises(jwt.InvalidAudienceError):
        verifier.identity(make_token(aud="account"))


def test_from_env_requires_the_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTH_ISSUER", raising=False)
    with pytest.raises(RuntimeError, match="AUTH_ISSUER"):
        TokenVerifier.from_env()


def test_from_env_uses_the_realm_jwks_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    urls: list[str] = []
    monkeypatch.setattr(jwt, "PyJWKClient", lambda url: urls.append(url))
    monkeypatch.setenv("AUTH_ISSUER", ISSUER)
    monkeypatch.delenv("AUTH_JWKS_URL", raising=False)

    TokenVerifier.from_env()

    assert urls == [f"{ISSUER}/protocol/openid-connect/certs"]
