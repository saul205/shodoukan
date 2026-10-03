# Authentication

[← Technical documentation](../README.md)

How users sign in, how requests are authenticated, and how they're matched to a
practice user. Code: `src/shodoukan_practice/api/auth.py`, `get_current_user` in
`api/deps.py`, `EnsureUser` in `application/commands/user_commands.py`. Local
identity provider: `docker/keycloak/`.

## Model

The practice API is an **OAuth2 resource server**. It never sees passwords; sign-up,
sign-in, password reset and sessions belong to the identity provider (**Keycloak**,
OpenID Connect). Why: [decisions](../decisions.md#external-identity-provider-instead-of-our-own-user-management).

1. The frontend (or the Swagger UI) sends the user to Keycloak's login page with the
   **authorization code flow + PKCE**, and gets back an access token.
2. Every API request carries `Authorization: Bearer <access token>`.
3. The API verifies the token and reads the user's identity: `sub` (stable id) and
   `preferred_username` (display name).
4. `EnsureUser` returns the practice user whose `id` **is** that `sub` (a UUID), **creating it
   on the first request** ([use cases](../application/use-cases.md#ensureuserusersexecuteuser_id-username)).

## Token verification (`TokenVerifier`)

| Check | Rule |
|---|---|
| Signature | RS256, against the realm's public keys (JWKS) |
| Keys | From `AUTH_JWKS_URL`, default `<AUTH_ISSUER>/protocol/openid-connect/certs`; cached by `PyJWKClient`, refetched for an unknown key id |
| `exp` | Required, must not be expired |
| `iss` | Required, must equal `AUTH_ISSUER` (the realm URL) |
| `aud` | Must contain `AUTH_AUDIENCE` when it's set (`shodoukan-practice` locally) |
| `sub` | Required, and must be a **UUID**: it is the practice user's `id` (`users.id`). Otherwise `401` |
| `preferred_username` | Optional; becomes `users.username` on creation (falls back to `sub`) |

`TokenVerifier.from_env()` builds it from the environment (see
[configuration](../cross-cutting/configuration.md#authentication)). In tests it's
built with a generated key instead (see [testing](../testing.md)).

## Errors

| Situation | Status |
|---|---|
| No bearer token, malformed, expired, bad signature, wrong issuer or audience, or a `sub` that isn't a UUID | `401`, with `WWW-Authenticate: Bearer` |

There's no "not registered" case: a valid token always has a practice user, created on
the first request if needed.

## Swagger UI login

The API declares an `OAuth2AuthorizationCodeBearer` security scheme (authorization
and token URLs of the realm), so `/docs` shows an **Authorize** button. The Swagger UI
is configured with `swagger_ui_init_oauth`: client `shodoukan-web` (override with
`AUTH_SWAGGER_CLIENT_ID`), PKCE on, scopes `openid profile`. The client's redirect
URIs include `http://localhost:8001/docs/oauth2-redirect`.

The scheme only extracts the bearer token; `TokenVerifier` does all the checking. Its
URLs are for the docs only, so they fall back to the local realm when `AUTH_ISSUER`
isn't set.

## Local Keycloak

`docker compose up -d keycloak` runs Keycloak 26.3 (`start-dev`) on
`http://localhost:8080` and imports the **`shodoukan` realm** from
`docker/keycloak/realm-shodoukan.json`. The realm is imported only when it doesn't
exist yet; see [configuration](../cross-cutting/configuration.md#keycloak) to
re-import it after editing the file.

| Realm setting | Value |
|---|---|
| Self-registration | on (Keycloak's own sign-up page) |
| Login with email, password reset, remember me, brute-force protection | on |
| Access token lifespan | 5 minutes |

| Client | Type | Use |
|---|---|---|
| `shodoukan-web` | public, authorization code + PKCE (S256) | the frontend (`http://localhost:3000/*`) and the Swagger UI (`http://localhost:8001/docs/oauth2-redirect`) |
| `shodoukan-dev-cli` | public, password grant | **local development only**: scripts and smoke tests (`curl -d grant_type=password ...`). Never enable it in a real realm. |

Both clients have an **audience mapper** adding `shodoukan-practice` to the access
token's `aud`, so `AUTH_AUDIENCE=shodoukan-practice` rejects tokens issued for other
purposes. Clients keep Keycloak's default scopes: `basic` provides `sub` and
`profile` provides `preferred_username`. Don't add a `clientScopes` list to the realm
file, because it would replace those built-in scopes.

Local user: `dev` / `dev` (only in the local realm file).

Getting a token from a script:

```bash
curl -s -X POST http://localhost:8080/realms/shodoukan/protocol/openid-connect/token \
  -d grant_type=password -d client_id=shodoukan-dev-cli -d username=dev -d password=dev
```

## Provider requirement: UUID subjects

Practice users are keyed by the provider's user id (`users.id = sub`, 1:1). Keycloak,
AWS Cognito and Supabase Auth issue UUID `sub`s. Auth0 (`auth0|…`), Google (numeric)
and Okta (opaque ids) don't, and their tokens would be rejected. Moving to one of
those would need an id-mapping column again. See
[decisions](../decisions.md#users-are-keyed-by-the-identity-providers-uuid).

## Production

Use the same code with a different provider configuration: a self-hosted Keycloak
(with its own database, HTTPS, no `shodoukan-dev-cli`, no dev user) or a managed OpenID
Connect provider. Only `AUTH_ISSUER`, `AUTH_AUDIENCE` and the frontend's client
settings change.
