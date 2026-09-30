---
name: python-backend-clean-code
description: Use when writing, reviewing, or planning Python backend code in this repo — packages/shodoukan, shodoukan-api, shodoukan-practice, and their tests/ counterparts. Covers PEP8/Ruff style, strict typing, layered clean architecture with dependency inversion (domain/application/infrastructure/api), module naming (<subject>_<role>.py, plural packages, singular classes), one-file-per-aggregate conventions, Protocol vs ABC repository interfaces, mapper naming (*_to_domain/*_to_db), SQLite-backed testing, and when (not) to introduce async.
---

# Python backend clean code

Conventions for backend Python work in this repo. `packages/shodoukan` (the core
library) predates most of this and is pragmatic rather than fully layered — don't
retrofit it. Apply these conventions going forward, especially in
`packages/shodoukan-practice`, which already follows this layering.

## Style & formatting

- PEP 8, enforced via Ruff (`ruff.toml` at repo root: `line-length = 88`, rules
  `E,W,F,I,UP,B,C4,SIM,RUF`).
- Run `ruff check`, `ruff format` and `mypy` before considering a change done.
- If you add a new first-party package, add its import name to
  `[lint.isort] known-first-party` in `ruff.toml`.

## Typing

- Explicit type hints on every public function/method signature. No implicit `Any`.
- Domain models are Pydantic classes — see
  `packages/shodoukan/src/shodoukan/models/entry.py`.
- ORM models use SQLAlchemy 2.0 style (`Mapped[...]`, `mapped_column`) — see
  `packages/shodoukan/src/shodoukan/db/orm.py`.
- Type checker: **mypy**, configured in `mypy.ini` at the repo root (with the
  `pydantic.mypy` plugin). Run `mypy` from the repo root; it checks the paths listed
  under `files` there. The developer also runs it through the VS Code mypy extension
  (`.vscode/settings.json` points it at `mypy.ini` and the `.venv`). CI runs it too.
- `strict = True` applies to `shodoukan_practice` and its tests. The core
  `shodoukan` / `shodoukan_api` packages predate mypy and aren't in `files`; don't
  retrofit them wholesale. Add a package to `files` (and a strict section) once it's
  clean.
- Let the types carry domain distinctions the checker can enforce: when two kinds of
  id would both be a bare `int` and could be confused (e.g. entry vs kanji collection
  ids, which come from different tables), take the typed entity
  (`KanjiCollection`) instead of the id. mypy is nominal, so two Pydantic subclasses
  with identical fields are still distinct types.

## Naming

A module's name states its role on its own, without relying on the folder it's in.

- **Module: `<subject>_<role>.py`.** `<subject>` is the snake_case aggregate (the class
  name without its role suffix: `PracticeKanjiRepository` → `practice_kanji`). `<role>`
  is singular when the file holds one thing of that kind, plural when it holds a set
  (`commands`, `queries`, `routes`, `schemas`).
- **Package/folder: plural** — it's a namespace holding many modules. Each package
  re-exports its public names from `__init__.py` via `__all__`, so callers import from
  the package (`from shodoukan_practice.domain.entities import PracticeKanji`).
- **Class: singular.** Entities are unsuffixed (`PracticeEntry`, not
  `PracticeEntryEntity`); everything else carries its role (`UserRepository`,
  `UserORM`). Concrete implementations are prefixed with their technology
  (`SqlAlchemyPracticeKanjiRepository`).
- **Spell the role out** (`_repository`, not `_repo`): it matches the class name and
  is greppable.
- **Tests: `test_<subject>_<role>.py`**, one per module under test.

| Role | Folder | Module | Classes / functions |
|---|---|---|---|
| Entity | `domain/entities/` | `practice_entry_entity.py` | `PracticeEntry` + its value objects |
| Repository interface | `domain/repositories/` | `practice_entry_repository.py` | `PracticeEntryRepository` |
| Domain service | `domain/services/` | `collection_service.py` | `ensure_combinable` |
| Use cases | `application/commands/`, `application/queries/` | `collection_commands.py`, `collection_queries.py` | one function/class per use case |
| ORM model | `infrastructure/db/orm/` | `practice_entry_orm.py` | `PracticeEntryORM` (+ its link tables) |
| Mapper | `infrastructure/db/mappers/` | `practice_entry_mapper.py` | `practice_entry_to_domain`, `practice_entry_to_db` |
| Concrete repository | `infrastructure/repositories/` | `sqlalchemy_practice_entry_repository.py` | `SqlAlchemyPracticeEntryRepository` |
| API routes / schemas | `api/routes/`, `api/schemas/` | `collection_routes.py`, `collection_schemas.py` | routers, request/response models |
| Test | `tests/<package>/<layer>/` | `test_collection_service.py` | `test_*` functions |

Cross-cutting single modules (`domain/exceptions.py`, `api/deps.py`, `api/app.py`)
stay as they are until they grow enough to split. A scaffold module that is still
only a docstring (e.g. `application/commands.py`) becomes a package following the
table when it gets its first real content.

The core `shodoukan` / `shodoukan_api` packages predate this convention (`models/entry.py`,
`repositories/mapper.py`); don't rename them wholesale.

## Entities: one file per aggregate

One file per aggregate root, not one file per class and not everything crammed into a
single `entities.py`. An aggregate file holds its root plus its nested value objects.

Examples:
- `packages/shodoukan-practice/src/shodoukan_practice/domain/entities/practice_entry_entity.py`
  — `PracticeEntry` plus `PracticeReading`, `PracticeSense`, `PracticeGloss`, etc.
- `.../domain/entities/collection_entity.py` — `Collection` base plus its
  `EntryCollection` / `KanjiCollection` subclasses.
- `packages/shodoukan/src/shodoukan/models/entry.py` — same split in the core library
  (older naming).

Aggregates change only through their own methods (`Collection.rename`,
`PracticeEntry.deactivate`, ...); use cases call methods instead of assigning fields
of a loaded aggregate. Aggregates inherit `TimestampedEntity`
(`domain/entities/timestamped_entity.py`): `created_at`/`updated_at` default to
`utc_now()`, and **every method that changes state calls `touch()`**, so
`updated_at` moves with any change. A call that changes nothing doesn't touch.
`validate_assignment` is on, so methods get the same validation as the constructor.

## Repositories: interfaces + dependency inversion

Target pattern for any package with write behavior (e.g. `shodoukan-practice`):

- `domain/repositories/<entity>_repository.py`, one file per repository, defines the
  interface — e.g. `practice_kanji_repository.py` (`PracticeKanjiRepository`),
  `kanji_collection_repository.py` (`KanjiCollectionRepository`), re-exported from
  `domain/repositories/__init__.py` via `__all__`. The domain layer depends only on
  these interfaces.
- Choose the interface style by context:
  - **`Protocol`** (default, used in `shodoukan-practice`): structural typing — the
    implementation doesn't need to import the domain, and mypy checks conformance
    wherever the object is passed. Concrete classes may still inherit the Protocol
    explicitly, so mypy checks them at the class definition and the intent is
    visible.
  - **`ABC`**: when you want a missing method to fail at instantiation (runtime
    enforcement, not just mypy), concrete helper methods shared by every
    implementation, or reliable `isinstance` checks.
- Concrete implementations live in
  `infrastructure/repositories/<tech>_<entity>_repository.py`, one file per
  repository, and inherit their Protocol explicitly
  (`class SqlAlchemyPracticeKanjiRepository(PracticeKanjiRepository)`) so mypy checks
  them at the definition. The tech prefix names the library, not the engine
  (`sqlalchemy_`: the same code runs on PostgreSQL and on SQLite in tests).
- Repositories receive a `Session` in `__init__`, `flush()` to get ids and surface
  constraint errors, and **never commit**: the use case / request that opened the
  session owns the transaction, so several repositories can share one unit of work.
- Every query is scoped to the owning user (`user_id`), directly or through the
  collection.
- `update(entity)` checks that the stored row exists and has the same `user_id`
  (else `EntityNotFoundError`), then `session.merge(<entity>_to_db(entity))`: nested
  items with an id are updated, items with `id=None` inserted, missing ones deleted
  (`delete-orphan`).
- Load nested snapshots eagerly with `selectinload` (one query per level, no N+1).
- Relationships held in link tables (e.g. collection membership) are read and
  changed through repository methods (`add_item`, `list_by_collection`, ...), not
  loaded onto the entity: pagination, ordering and set operations belong in SQL.
- Concrete repositories are injected into the API layer via FastAPI `Depends`,
  following the pattern already used (without an interface yet) in
  `packages/shodoukan-api/src/shodoukan_api/deps.py` (`dictionary_dep`).

`packages/shodoukan` (core) does not follow this — its repositories are concrete
classes with no interface, constructed directly. That's fine for a read-only library;
don't retrofit it. New write-capable packages should use interfaces from the start.

## Database & migrations (shodoukan-practice)

- Target engine is **PostgreSQL**; tests run on SQLite, so use only portable column
  types (e.g. `sa.JSON`, not `JSONB`).
- **Dates: naive UTC in the database, aware UTC in the backend, ISO with offset in
  the API.** Datetime columns use `UtcDateTime` from `orm/base_orm.py`
  (`timestamp without time zone`): it converts aware datetimes to UTC and strips the
  zone on write, attaches UTC on read, and rejects naive datetimes instead of guessing
  their zone. Domain entities and use cases only handle aware UTC datetimes
  (`utc_now()` from `domain/clock.py`); Pydantic serializes them with the offset
  (`...Z`) and clients convert to local time.
- **"Now" is decided by the domain, not the database or the ORM.** Entities default
  their timestamps via `TimestampedEntity` and bump `updated_at` with `touch()`; the
  mapper copies them to the row. Timestamp columns have no `default`, `onupdate` or
  `server_default`, so a missing one fails instead of being invented by persistence.
  Rows with no entity behind them (e.g. `added_at` in collection link tables) get
  `utc_now()` from the repository that inserts them.
- Why no database defaults for timestamps: they only pay off when something writes
  to the database without going through the app (SQL scripts, bulk loads, another
  service), or when a trigger must stamp *every* write. Here they would hide the
  dates from the entity until after the insert, fight the domain's `updated_at`,
  make time hard to control in tests, and need dialect-specific SQL (on a naive
  column PostgreSQL needs `timezone('utc', now())`, which SQLite lacks). Performance
  and scale are the same either way. Revisit if a non-app writer appears: then add
  `server_default` as a safety net, keeping the domain as the source of the value.
- ORM models: `infrastructure/db/orm/<entity>_orm.py`, all on the `Base` from
  `orm/base_orm.py`, whose `naming_convention` gives every constraint a stable name.
  Owned child rows use `children("<Model>.position")` (ordered, cascade delete);
  their FKs use `ondelete="CASCADE"`. Enum-like strings get a named `CheckConstraint`.
  Link tables are plain `Table` objects with no ORM relationship: repositories query
  them explicitly.
- Non-time defaults live in both places: `default=` for the ORM and
  `server_default=` for the database, so raw SQL inserts get them too.
- Alembic's `env.py` has a `render_item` hook that writes custom types such as
  `UtcDateTime` as their plain SQLAlchemy type, so migrations never import app code.
- Migrations: Alembic, `packages/shodoukan-practice/alembic.ini`, scripts in
  `infrastructure/db/migrations/versions/`. Every model change ships with a migration:
  `alembic -c packages/shodoukan-practice/alembic.ini revision --autogenerate -m
  "<Summary>"` against the local Postgres, then review the generated file by hand.
- `tests/shodoukan-practice/infrastructure/test_migrations.py` fails if the migrations
  and the models drift apart; CI also runs upgrade/check/downgrade on real Postgres.
- The URL comes only from `PRACTICE_DATABASE_URL` (no default in code). Credentials
  live in the gitignored `.env.dev`; `.env.example` documents every variable.

## Mappers

One mapper file per aggregate, mirroring the entity split — not a single catch-all
`mappers.py`: `infrastructure/db/mappers/<entity>_mapper.py`, next to the ORM models in
`infrastructure/db/orm/<entity>_orm.py`. Function naming (from
`packages/shodoukan/src/shodoukan/repositories/mapper.py`):

- `<entity>_to_domain(row: XxxORM) -> Xxx` — ORM row to domain model.
- `<entity>_to_db(entity: Xxx) -> XxxORM` — domain model to ORM row. Required for any
  write path (the core `shodoukan` library is read-only, so it only has `_to_domain`).

## Layers (clean architecture)

Follow the layering already scaffolded in `packages/shodoukan-practice`:

- `domain/` — entities, repository interfaces (ports), pure business logic
  (`domain/services/`). No imports from `infrastructure/` or `api/`.
- `application/` — use cases: commands that write, queries that read (see Naming for
  file layout). Orchestrates domain objects and repository interfaces; knows nothing
  about FastAPI or SQLAlchemy.
- `infrastructure/` — ORM models, mappers, concrete repository implementations, DB
  connection setup.
- `api/` — FastAPI routes, request/response schemas, dependency wiring (`deps.py`).

Each layer only depends on the layers it's allowed to: `api` → `application` →
`domain`, with `infrastructure` implementing `domain` interfaces and being wired in at
the `api` layer.

## Scalability & maintainability

- Avoid catch-all modules. Prefer simple composition over premature abstraction.
- Three similar lines is fine — don't introduce an abstraction until a third real
  repetition shows what the abstraction should actually look like.

## Async: a maturity ladder, not a default

Every backend package in this repo is synchronous today (no `async def`,
`AsyncSession`, or `create_async_engine` anywhere). Starting synchronous is the right
call while there's no real concurrency need.

Before introducing `async def` routes/repositories (`AsyncSession`,
`create_async_engine`), agree it explicitly with the developer first — don't add the
complexity ahead of a proven need (real concurrent load, genuinely IO-bound waits in
practice).

## Testing

Real SQLite as the "mock" database — never mock the repository or the ORM directly.

- `tests/db_helpers.py` — shared schema + seed data.
- `tests/shodoukan/conftest.py` — `conn` fixture opens
  `sqlite3.connect(":memory:")`, builds the schema, seeds it; `engine` fixture wraps
  it via `open_test_connection` with `StaticPool` so every session reuses the same
  in-memory connection (a plain SQLAlchemy engine would otherwise open a new, empty
  `:memory:` DB per connection).
- `tests/shodoukan-practice/infrastructure/conftest.py` — same idea for the practice
  ORM: `sqlite://` + `StaticPool`, `PRAGMA foreign_keys = ON` (SQLite ignores FKs and
  `ON DELETE CASCADE` otherwise) and `Base.metadata.create_all`.
- One test file per module under test, named `test_<subject>_<role>.py` — see
  `tests/shodoukan/test_entry_repository.py` and
  `tests/shodoukan-practice/domain/test_collection_service.py`: plain pytest
  functions, no mocking framework, assertions on domain objects returned from a real
  call.

## Package documentation

Per `CLAUDE.md`: any new package or significant architectural decision needs a doc
update — add an entry to `docs/index.md` plus `docs/functional/<package>.md` /
`docs/technical/<package>.md` once the package has real functionality (a scaffold
with no behavior yet, like `shodoukan-practice` today, doesn't need one).

See `.claude/rules/git-and-docs.md` for git, documentation, and changelog conventions
that apply repo-wide, not just to Python.
