# Testing

[← Technical documentation](README.md)

How the practice app is tested and what each group of tests covers.

```bash
pytest tests/shodoukan-practice
mypy        # strict for shodoukan_practice and its tests (mypy.ini)
ruff check packages/shodoukan-practice tests/shodoukan-practice
```

## Principles

- Real SQLite (in memory) as the test database. Repositories and the ORM are never
  mocked.
- One test file per module under test: `test_<subject>_<role>.py`.
- Plain pytest functions with assertions on domain objects.

## Layout

| Folder / file | Covers |
|---|---|
| `domain/test_*_entity.py` | Entity shape, defaults, validation, mutation methods (notes, enabled parts, own meanings, dictionary data protected) and `touch()` |
| `domain/test_notes_value.py` | Notes cleaning and length limit |
| `domain/test_timestamped_entity.py` | Timestamp defaults, `touch()` |
| `domain/test_collection_service.py` | `ensure_combinable` |
| `infrastructure/test_base_orm.py` | `UtcDateTime`: naive UTC stored, aware UTC read, naive rejected, no DB default |
| `infrastructure/test_*_orm.py` | Constraints, cascades, `position` ordering |
| `infrastructure/test_*_mapper.py` | `to_domain(to_db(entity)) == entity` without a database |
| `infrastructure/test_sqlalchemy_*_repository.py` | Each repository through its port, including owner scoping and membership |
| `infrastructure/test_migrations.py` | Migrations match the models; downgrade works |
| `infrastructure/test_shodoukan_mapper.py` | Dictionary models → fresh practice entities, every language kept |
| `infrastructure/test_shodoukan_dictionary_gateway.py` | The gateway against a real seeded dictionary: snapshots, search by Japanese, romaji and meaning, and entry/kanji details |
| `application/test_library_commands.py` | Import use cases with real repositories and the real gateway: created, already imported, per-user copies, not found |
| `application/test_dictionary_queries.py` | Dictionary detail queries: found, not found, words for a kanji, kanji of an entry |
| `application/test_library_queries.py` | `GetImportStatus`: only the user's imports, empty input; `ListLibraryEntries` / `ListLibraryKanji`: page with total, `active` filter |
| `application/test_collection_commands.py` | Collection commands: create, duplicate names, update and `updated_at`, delete keeps items, idempotent membership, other users' collections and items not found |
| `application/test_collection_queries.py` | Listing and getting collections, paging a collection's active items, owner scoping |
| `application/test_practice_entry_commands.py`, `test_practice_kanji_commands.py` | Customisation use cases: notes, active, enabled, own meanings, dictionary meanings rejected, other users' items, removal from the library |
| `application/test_user_commands.py` | `EnsureUser`: existing identity, first request creates, no duplicates |
| `api/test_library_routes.py` | The library endpoints through `TestClient`: listing (newest first, total, paging, `active`, owner scoping, ids usable in collections), import (201/200/404/422/401), import status (only the user's imports, limits, validation), user creation on first request, CORS preflight |
| `api/test_collection_routes.py` | The collection endpoints: create/get/list/update/delete, name validation and `409`, items (add, list, page, remove), other users' collections `404`, `401`, CORS for `DELETE` |
| `api/test_practice_entry_routes.py`, `test_practice_kanji_routes.py` | Library item endpoints: detail, notes (and validation), active, enabled per part, own meanings, 409 for dictionary meanings, collections of an item, removal, other users' items `404`, `401` |
| `api/test_dictionary_routes.py` | `GET /dictionary/search` and the detail routes: public, the same shape as shodoukan-api, pagination, validation, 404s, and that results can be imported |
| `api/test_user_routes.py` | `GET /users/me`, and the OAuth2 login declared in the OpenAPI schema |
| `api/test_auth.py` | `TokenVerifier`: identity, expiry, issuer, signature, audience, configuration |

## Fixtures and helpers

All fixtures live in `tests/shodoukan-practice/conftest.py`, so every test folder can
use them. There's a single `conftest.py` because mypy rejects two modules with the
same name in folders that aren't packages.

- `engine`: in-memory SQLite configured for the tests:
  - `StaticPool`, so every session shares the same in-memory database;
  - `check_same_thread=False`, because `TestClient` runs endpoints in a worker thread;
  - `PRAGMA foreign_keys = ON`, since SQLite ignores FKs and `ON DELETE CASCADE`
    otherwise;
  - SQLAlchemy emits `BEGIN` itself (`isolation_level = None` plus a `begin` event),
    because pysqlite's own transaction handling breaks savepoints (`begin_nested`,
    used by `add_if_absent`);
  - `Base.metadata.create_all`.
- `session`, `user` (`id=USER_ID`), `other_user` (`id=OTHER_USER_ID`).
- `dictionary`: a real `shodoukan.Dictionary` over a temporary SQLite, built with the
  core library's `SCHEMA` and `seed` from `tests/db_helpers.py` (`auto_download=False`).
- API: `signing_key` (an RSA key generated per test run), `make_token(subject, ...)`
  (signs RS256 tokens with overridable claims; the default `sub` is `str(USER_ID)`), `verifier` (a `TokenVerifier` given
  the matching public key), and `client` (a `TestClient` with `get_session`,
  `get_dictionary_gateway` and `get_token_verifier` overridden).
- Helper modules next to `conftest.py`:
  - `factories.py`: `USER_ID` / `OTHER_USER_ID` (fixed UUIDs), `make_entry`,
    `make_kanji`, `make_*_collection`, `NOW`, and
    `TIMESTAMPS` for ORM rows built directly;
  - `tokens.py`: `ISSUER`, `DEFAULT_SUBJECT`, `TokenFactory`, `bearer(token)`.

## Against the real Keycloak

The unit tests use locally signed tokens. To check the real sign-in end to end, start
`practice-db` and `keycloak`, run the API on port 8001, get a token (password grant
with `shodoukan-dev-cli`, see [authentication](api/authentication.md#local-keycloak)),
and call `/users/me`. Scripting the browser flow (authorization code + PKCE with
`shodoukan-web`) also works, but Keycloak's session cookies are `Secure`: browsers send
them on `http://localhost`, while scripted HTTP clients have to forward them by hand.

## CI

`.github/workflows/ci.yml` installs the package, runs `mypy` and
`pytest tests/shodoukan-practice`, then runs the migrations against a throwaway
`postgres:16-alpine` service: `upgrade head`, `check`, `downgrade base`, `upgrade head`.

A separate `frontend` job installs the pnpm workspace (`--frozen-lockfile`), builds and
tests `shodoukan-ui`, and runs the practice frontend's Vitest suite and `nuxt
typecheck`. See [frontend](frontend.md#tests).
