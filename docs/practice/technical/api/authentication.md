# Authentication

[← Technical documentation](../README.md)

How requests are authenticated and matched to a practice user. Code:
`src/shodoukan_practice/api/auth.py` and `get_current_user` in `api/deps.py`.

## Model

The practice API is an **OAuth2 resource server**. It never sees passwords:

1. The frontend signs the user in with **Keycloak** (OIDC) and gets an access token.
2. Every request carries `Authorization: Bearer <access token>`.
3. The API verifies the token and takes the user's identity from its `sub` claim.
4. The `sub` is looked up as `users.subject`; that's the practice user.

## Token verification (`TokenVerifier`)

| Check | Rule |
|---|---|
| Signature | RS256, against the realm's public keys (JWKS) |
| Keys | Fetched from `AUTH_JWKS_URL`, default `<AUTH_ISSUER>/protocol/openid-connect/certs`; cached by `PyJWKClient`, refetched for an unknown key id |
| `exp` | Required, must not be expired |
| `iss` | Required, must equal `AUTH_ISSUER` (the realm URL) |
| `aud` | Checked only when `AUTH_AUDIENCE` is set |
| `sub` | Required |

On `aud`: Keycloak only adds a custom audience to access tokens when an *audience
mapper* is configured for the client. Configure one and set `AUTH_AUDIENCE` so tokens
issued for other clients of the realm are rejected.

`TokenVerifier.from_env()` builds the verifier from the environment; see
[configuration](../cross-cutting/configuration.md). In tests, it's built with a
generated key instead (see [testing](../testing.md)).

## Errors

| Situation | Status |
|---|---|
| No bearer token, malformed, expired, bad signature, wrong issuer/audience | `401`, with `WWW-Authenticate: Bearer` |
| Valid token, but no practice user with that `sub` | `403` (`user not registered`) |

There's no registration use case yet, so users are created outside the API for now.
