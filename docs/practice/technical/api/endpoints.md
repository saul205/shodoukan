# Endpoints

[← Technical documentation](../README.md)

The HTTP API of the practice app. Code: `src/shodoukan_practice/api/`
(`app.py`, `routes/`, `schemas/`, `deps.py`). Interactive docs at `/docs` when running.

Every endpoint requires a bearer token; see [authentication](authentication.md).

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
| `401` / `403` | See [authentication](authentication.md#errors) | `{"detail": ...}` |
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
| `get_current_user` | the registered `User` behind the bearer token |
| `get_dictionary_gateway` | `ShodoukanDictionaryGateway` over a cached `Dictionary()` |
| `get_import_entry` / `get_import_kanji` | use cases with SQLAlchemy repositories on the request's session |

Tests replace `get_session`, `get_dictionary_gateway` and `get_token_verifier` with
`app.dependency_overrides`.
