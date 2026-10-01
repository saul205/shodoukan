from datetime import timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from tokens import ISSUER, TokenFactory

from shodoukan_practice.api.auth import TokenVerifier


def test_valid_token_gives_its_subject(
    verifier: TokenVerifier, make_token: TokenFactory
) -> None:
    assert verifier.subject(make_token("sub-123")) == "sub-123"


def test_expired_token_is_rejected(
    verifier: TokenVerifier, make_token: TokenFactory
) -> None:
    with pytest.raises(jwt.ExpiredSignatureError):
        verifier.subject(make_token(expires_in=timedelta(minutes=-1)))


def test_other_issuer_is_rejected(
    verifier: TokenVerifier, make_token: TokenFactory
) -> None:
    with pytest.raises(jwt.InvalidIssuerError):
        verifier.subject(make_token(issuer="https://evil.test/realms/x"))


def test_token_signed_by_another_key_is_rejected(
    verifier: TokenVerifier, make_token: TokenFactory
) -> None:
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(jwt.InvalidSignatureError):
        verifier.subject(make_token(key=other_key))


def test_audience_is_checked_when_configured(
    signing_key: rsa.RSAPrivateKey, make_token: TokenFactory
) -> None:
    public_key = signing_key.public_key()
    verifier = TokenVerifier(ISSUER, "shodoukan-practice", lambda _: public_key)

    assert verifier.subject(make_token(aud="shodoukan-practice")) == "sub-saul"
    with pytest.raises(jwt.InvalidAudienceError):
        verifier.subject(make_token(aud="account"))


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
