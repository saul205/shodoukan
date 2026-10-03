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
sign-in through Keycloak (users auto-created on first request, `GET /users/me`), importing an entry or kanji (`POST /library/entries`, `POST /library/kanji`), and public
dictionary search (`GET /dictionary/search`, same `Dictionary.search` as shodoukan-api),
the import status of search results (`GET /library/imported`), listing the library
(`GET /library/entries`, `GET /library/kanji`, paged with a total), and collections
(`/collections/entries`, `/collections/kanji`: CRUD plus adding, removing and paging
items). The practice and dictionary apps are standalone: never call shodoukan-api from
here. Not built yet: customisation endpoints, exercises.

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
- `application/commands/user_commands.py`: `EnsureUser` (creates the user on first use).
- `application/commands/collection_commands.py` / `queries/collection_queries.py`:
  collection use cases, one class per use case and kind (`CreateEntryCollection`,
  `AddKanjiToCollection`, `ListEntryCollectionItems`, ...).
- `application/queries/library_queries.py`: `GetImportStatus`, `ListLibraryEntries`,
  `ListLibraryKanji` (return `LibraryPage(items, total, limit, offset)`);
  `queries/dictionary_queries.py`: `SearchDictionary`.
- Dictionary read models (`DictionaryEntry`, `DictionarySearchResult`, ...) live with
  the port in `domain/gateways/dictionary_gateway.py`.
- `api/`: `app.py` (maps `EntityNotFoundError` → 404, `CollectionNameTakenError` →
  409), `auth.py` (`TokenVerifier`), `deps.py` (one session per request; routes
  commit), `routes/*_routes.py`, `schemas/*_schemas.py`.
- `infrastructure/repositories/`: `sqlalchemy_*_repository.py`.
- `infrastructure/dictionary/`: `ShodoukanDictionaryGateway` and `shodoukan_mapper.py`
  (the anti-corruption layer). Wired in `api/deps.py` (cached `Dictionary()`).

## Domain rules specific to this app

- Entry and kanji collections are separate subclasses (`EntryCollection`,
  `KanjiCollection`) and never mixed. Ports take the typed collection, never an id.
- Collections are metadata only. Membership lives in `entry_collection_items` /
  `kanji_collection_items` and goes through the collection repositories.
- Every query is scoped to `user_id`. `update()` raises `EntityNotFoundError` for a
  missing or foreign row; the API answers 404 for both.
- Collection names: 1–100 characters, unique per user and kind. The repository turns
  the unique-constraint violation into `CollectionNameTakenError` (savepoint).
- `User.id` **is** the identity provider's user id (the token's `sub`, a UUID); every
  `user_id` is a `UUID`. Users are created on their first request. A non-UUID `sub` →
  401. `username` is a display name, not unique.
- Migrations are append-only from now on (the pre-deploy history was squashed into one
  initial migration).
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

## Auth (Keycloak)

- Local identity provider: `docker compose up -d keycloak` (it starts its own
  `keycloak-db`; env in `.env.keycloak`, from `.env.keycloak.example`). The realm is
  `docker/keycloak/realm-shodoukan.json`: clients `shodoukan-web` (PKCE; frontend and
  Swagger) and `shodoukan-dev-cli` (password grant, local only), user `dev`/`dev`.
- API env (`.env.dev`): `AUTH_ISSUER=http://localhost:8080/realms/shodoukan`,
  `AUTH_AUDIENCE=shodoukan-practice`.
- Run: `uvicorn shodoukan_practice.api.app:app --port 8001 --reload`; `/docs` has
  **Authorize** (Keycloak login).
- VS Code: the **Practice API** launch configuration starts the services, migrates
  (task `practice: prepare`) and runs the API with the debugger.
- Token for scripts: `curl -s -X POST http://localhost:8080/realms/shodoukan/protocol/openid-connect/token -d grant_type=password -d client_id=shodoukan-dev-cli -d username=dev -d password=dev`.
- Details: `docs/practice/technical/api/authentication.md`.

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
