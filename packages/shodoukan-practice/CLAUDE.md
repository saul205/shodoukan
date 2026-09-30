# shodoukan-practice

Practice/exercises backend: each user's library of imported entries and kanji, and
their collections. Follows the `python-backend-clean-code` skill fully. This file holds
the package's specifics. The full technical reference is in
[`docs/practice/technical/`](../../docs/practice/technical/README.md); read the page
for the area you're touching, and update it in the same commit (see the "where to
document what" table there).

## Status

Built: domain, PostgreSQL persistence (ORM, Alembic), mappers, SQLAlchemy repositories.
Scaffolds only: `application/`, `api/`. Use cases and exercises aren't defined yet.

## Layout

`src/shodoukan_practice/`:

- `domain/`
  - `entities/`: `practice_entry_entity.py`, `practice_kanji_entity.py`,
    `user_entity.py`, `collection_entity.py`, and `timestamped_entity.py`
    (`TimestampedEntity` with `touch()`).
  - `repositories/`: Protocol ports.
  - `services/collection_service.py`: `ensure_combinable`.
  - `exceptions.py`, and `clock.py` with `utc_now()`.
- `infrastructure/db/`
  - `orm/`: `base_orm.py` (`Base`, `UtcDateTime`, `children()`) plus one `*_orm.py`
    per aggregate.
  - `mappers/`, `migrations/`, `connection.py`.
- `infrastructure/repositories/`: `sqlalchemy_*_repository.py`.

## Domain rules specific to this app

- Entry and kanji collections are separate subclasses (`EntryCollection`,
  `KanjiCollection`) and never mixed. Ports take the typed collection, never an id.
- Collections are metadata only. Membership lives in `entry_collection_items` /
  `kanji_collection_items` and goes through the collection repositories.
- Every query is scoped to `user_id`. `update()` raises `EntityNotFoundError` for a
  missing or foreign row.
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

## Tests

- `pytest tests/shodoukan-practice` (domain + infrastructure).
- `tests/shodoukan-practice/infrastructure/conftest.py`: SQLite `StaticPool` engine with
  FKs on. Fixtures `engine`, `session`, `user`, `other_user`.
- `infrastructure/factories.py`: `make_entry`, `make_kanji`, `make_*_collection`,
  `NOW`, `TIMESTAMPS`.
- `infrastructure/test_migrations.py` is the migration drift test. CI also runs the
  migrations on a throwaway PostgreSQL.
