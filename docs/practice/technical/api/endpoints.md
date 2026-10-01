# Endpoints

[← Technical documentation](../README.md)

The HTTP API of the practice app. Code: `src/shodoukan_practice/api/`
(`app.py`, `routes/`, `schemas/`, `deps.py`). Interactive docs at `/docs` when running.

Every endpoint requires a bearer token; see [authentication](authentication.md). The
app runs on port **8001** (`shodoukan-api` uses 8000):
`uvicorn shodoukan_practice.api.app:app --port 8001` or `shodoukan-practice`.

## `POST /library/entries`

Imports a dictionary entry into the current user's library
([`ImportEntry`](../application/use-cases.md#importentrydictionary-entriesexecuteuser_id-source_entry_id)).

Request body:

```json
{ "entry_id": 1358280 }
```

| Status | When | Body |
|---|---|---|
| `201` | Imported now | `PracticeEntryResponse` |
| `200` | Already in the library | the existing `PracticeEntryResponse` |
| `401` | See [authentication](authentication.md#errors) | `{"detail": ...}` |
| `404` | Not in the dictionary | `{"detail": ...}` |
| `422` | Invalid body | validation errors |

`PracticeEntryResponse`: `id`, `source_entry_id`, `kanji_readings`, `readings`,
`senses` (with `glosses` and `examples`), `jlpt`, `is_common`, `is_active`,
`created_at`, `updated_at`. Nested items carry their `id`, `enabled` and, where
applicable, `origin`. `user_id` isn't exposed.

## `POST /library/kanji`

Imports a dictionary kanji
([`ImportKanji`](../application/use-cases.md#importkanjidictionary-kanjiexecuteuser_id-literal)).

Request body (`literal` must be exactly one character):

```json
{ "literal": "食" }
```

Same status codes as above. `PracticeKanjiResponse`: `id`, `literal`, `grade`,
`stroke_count`, `freq`, `jlpt`, `on_readings`, `kun_readings`, `nanori`, `meanings`,
`is_active`, `created_at`, `updated_at`.

## `GET /users/me`

The current user's practice profile. On the first request of a new identity, the user
is created ([`EnsureUser`](../application/use-cases.md#ensureuserusersexecuteuser_id-username)),
so the frontend can call this right after sign-in.

| Status | When | Body |
|---|---|---|
| `200` | Always, for a valid token | `UserResponse`: `id` (the identity provider's user id, a UUID: equal to the token's `sub`), `username`, `created_at` |
| `401` | Missing or invalid token | `{"detail": ...}` |


## Conventions

- **Schemas** (`schemas/<subject>_schemas.py`) are separate from domain entities, so the
  API contract doesn't change when the domain does. Responses are built with
  `model_validate(entity)` (`from_attributes`).
- **Dates** are ISO 8601 UTC with `Z`; see [dates](../cross-cutting/dates-and-time-zones.md).
- **Domain errors → HTTP:** `DictionaryItemNotFoundError` → `404` (exception handler
  in `app.py`). Authentication errors are raised as `HTTPException`s in `deps.py`.

## Transactions

`deps.get_session()` opens one `Session` per request, shared by the repositories
built for it. Routes **commit explicitly** after the use case succeeds and before
responding, so a commit failure can't follow a success response. Anything not
committed is rolled back when the session closes.

## Wiring (`deps.py`)

| Dependency | Provides |
|---|---|
| `get_session` | the request's `Session` |
| `get_token_verifier` | `TokenVerifier.from_env()`, cached per process |
| `_oauth2` | the OAuth2 (authorization code) security scheme: extracts the bearer token and documents the Keycloak login for Swagger |
| `get_current_user` | the `User` behind the bearer token, created on first use (`EnsureUser`) |
| `get_dictionary_gateway` | `ShodoukanDictionaryGateway` over a cached `Dictionary()` |
| `get_import_entry` / `get_import_kanji` | use cases with SQLAlchemy repositories on the request's session |

Tests replace `get_session`, `get_dictionary_gateway` and `get_token_verifier` with
`app.dependency_overrides`.
