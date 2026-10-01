# shodoukan-practice

Practice/exercises backend: each user's library of imported entries and kanji, and
their collections. Follows the `python-backend-clean-code` skill fully. This file holds
the package's specifics. The full technical reference is in
[`docs/practice/technical/`](../../docs/practice/technical/README.md); read the page
for the area you're touching, and update it in the same commit (see the "where to
document what" table there).

## Status

Built: domain, PostgreSQL persistence (ORM, Alembic), mappers, SQLAlchemy repositories,
the dictionary integration (in-process `shodoukan` library behind `DictionaryGateway`),
and the first feature: importing an entry or kanji (`POST /library/entries`,
`POST /library/kanji`) with Keycloak bearer-token auth. Not built yet: user
registration, collections and customisation endpoints, exercises.

## Layout

`src/shodoukan_practice/`:

- `domain/`
  - `entities/`: `practice_entry_entity.py`, `practice_kanji_entity.py`,
    `user_entity.py`, `collection_entity.py`, and `timestamped_entity.py`
    (`TimestampedEntity` with `touch()`).
  - `repositories/`: Protocol ports.
  - `gateways/dictionary_gateway.py`: `DictionaryGateway`, the read-only dictionary port.
  - `services/collection_service.py`: `ensure_combinable`.
  - `exceptions.py`, and `clock.py` with `utc_now()`.
- `infrastructure/db/`
  - `orm/`: `base_orm.py` (`Base`, `UtcDateTime`, `children()`) plus one `*_orm.py`
    per aggregate.
  - `mappers/`, `migrations/`, `connection.py`.
- `application/commands/library_commands.py`: `ImportEntry`, `ImportKanji`
  (idempotent, return `ImportResult(item, created)`).
- `application/queries/user_queries.py`: `GetRegisteredUser`.
- `api/`: `app.py`, `auth.py` (`TokenVerifier`), `deps.py` (one session per request;
  routes commit), `routes/library_routes.py`, `schemas/library_schemas.py`.
- `infrastructure/repositories/`: `sqlalchemy_*_repository.py`.
- `infrastructure/dictionary/`: `ShodoukanDictionaryGateway` and `shodoukan_mapper.py`
  (the anti-corruption layer). Wired in `api/deps.py` (cached `Dictionary()`).

## Domain rules specific to this app

- Entry and kanji collections are separate subclasses (`EntryCollection`,
  `KanjiCollection`) and never mixed. Ports take the typed collection, never an id.
- Collections are metadata only. Membership lives in `entry_collection_items` /
  `kanji_collection_items` and goes through the collection repositories.
- Every query is scoped to `user_id`. `update()` raises `EntityNotFoundError` for a
  missing or foreign row.
- Users are identified by `User.subject` (the token's `sub`). Unknown subjects get
  `403`: users aren't created on first request.
- Imports keep every language. Importing again returns the existing copy (`200`);
  `add_if_absent` uses a savepoint to handle concurrent duplicates.
- Mutating methods so far: `Collection.rename` / `describe` and
  `PracticeEntry` / `PracticeKanji.activate` / `deactivate`. Add new ones with their use
  cases; each calls `touch()`.

## Database

- **PostgreSQL** in every real environment; unit tests use in-memory SQLite.
- URL: `PRACTICE_DATABASE_URL` (required, no default). Local values in `.env.dev`,
  documented in `.env.example`.
- Local database: `docker compose up -d practice-db`, then export the env file
  (`set -a; . ./.env.dev; set +a`).
- Migrations, run from the repo root:

  ```bash
  alembic -c packages/shodoukan-practice/alembic.ini revision --autogenerate -m "Describe the change"
  alembic -c packages/shodoukan-practice/alembic.ini upgrade head
  alembic -c packages/shodoukan-practice/alembic.ini check
  ```

## Auth

`AUTH_ISSUER` (Keycloak realm URL) is required to serve requests. `AUTH_AUDIENCE` and
`AUTH_JWKS_URL` are optional. See `docs/practice/technical/api/authentication.md`.

```bash
AUTH_ISSUER=https://keycloak.example/realms/shodoukan uvicorn shodoukan_practice.api.app:app --reload
```

## Tests

- `pytest tests/shodoukan-practice` (domain + infrastructure).
- `tests/shodoukan-practice/conftest.py` (the only conftest; mypy rejects duplicate
  module names): SQLite engine with FKs on, savepoint-safe, cross-thread for
  `TestClient`. Fixtures: `engine`, `session`, `user`, `other_user`, `dictionary`,
  `signing_key`, `make_token`, `verifier`, `client`.
- Helpers next to it: `factories.py` (`make_entry`, `make_kanji`, `make_*_collection`,
  `NOW`, `TIMESTAMPS`) and `tokens.py` (`ISSUER`, `bearer`).
- The `dictionary` fixture is a real `shodoukan.Dictionary` seeded from the core
  `tests/db_helpers.py`.
- Layout: `domain/`, `application/`, `infrastructure/`, `api/`.
- `infrastructure/test_migrations.py` is the migration drift test. CI also runs the
  migrations on a throwaway PostgreSQL.
