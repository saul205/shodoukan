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
| `domain/test_*_entity.py` | Entity shape, defaults, validation, mutation methods and `touch()` |
| `domain/test_timestamped_entity.py` | Timestamp defaults, `touch()` |
| `domain/test_collection_service.py` | `ensure_combinable` |
| `infrastructure/test_base_orm.py` | `UtcDateTime`: naive UTC stored, aware UTC read, naive rejected, no DB default |
| `infrastructure/test_*_orm.py` | Constraints, cascades, `position` ordering |
| `infrastructure/test_*_mapper.py` | `to_domain(to_db(entity)) == entity` without a database |
| `infrastructure/test_sqlalchemy_*_repository.py` | Each repository through its port, including owner scoping and membership |
| `infrastructure/test_migrations.py` | Migrations match the models; downgrade works |
| `infrastructure/test_shodoukan_mapper.py` | Dictionary models → fresh practice entities, every language kept |
| `infrastructure/test_shodoukan_dictionary_gateway.py` | The gateway against a real seeded dictionary |
| `application/test_library_commands.py` | Import use cases with real repositories and the real gateway: created, already imported, per-user copies, not found |
| `application/test_user_queries.py` | `GetRegisteredUser` |
| `api/test_library_routes.py` | The endpoints through `TestClient`: 201/200/404/422/401/403 |
| `api/test_auth.py` | `TokenVerifier`: expiry, issuer, signature, audience, configuration |

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
- `session`, `user` (`subject="sub-saul"`), `other_user`.
- `dictionary`: a real `shodoukan.Dictionary` over a temporary SQLite, built with the
  core library's `SCHEMA` and `seed` from `tests/db_helpers.py` (`auto_download=False`).
- API: `signing_key` (an RSA key generated per test run), `make_token(subject, ...)`
  (signs RS256 tokens with overridable claims), `verifier` (a `TokenVerifier` given
  the matching public key), and `client` (a `TestClient` with `get_session`,
  `get_dictionary_gateway` and `get_token_verifier` overridden).
- Helper modules next to `conftest.py`:
  - `factories.py`: `make_entry`, `make_kanji`, `make_*_collection`, `NOW`, and
    `TIMESTAMPS` for ORM rows built directly;
  - `tokens.py`: `ISSUER`, `TokenFactory`, `bearer(token)`.

## CI

`.github/workflows/ci.yml` installs the package, runs `mypy` and
`pytest tests/shodoukan-practice`, then runs the migrations against a throwaway
`postgres:16-alpine` service: `upgrade head`, `check`, `downgrade base`, `upgrade head`.
