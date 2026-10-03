---
name: python-backend-clean-code
description: Use when writing, reviewing, or planning Python backend code (FastAPI, SQLAlchemy 2.0, Pydantic, Alembic). Covers PEP 8/Ruff style, strict typing with mypy, layered clean architecture with dependency inversion (domain/application/infrastructure/api), module naming (<subject>_<role>.py, plural packages, singular classes), aggregates that change only through methods, Protocol vs ABC repository ports, repository and transaction rules, mappers (*_to_domain/*_to_db), persistence and date handling, migrations, testing against a real database, async adoption, and documenting on the fly.
---

# Python backend clean code

How to build and review a layered Python backend. These are general conventions; the
project's `CLAUDE.md` files (root and per package) give the specifics: paths, commands,
tool configuration, and which legacy code predates these rules.

**Before starting:** read the project's `CLAUDE.md` for the package you're touching. If
existing code predates these conventions, follow them in new code but don't retrofit old
code wholesale unless asked.

Examples below use a dictionary/practice domain (`PracticeEntry`, `KanjiCollection`, ...)
purely as illustration.

## Style & formatting

- PEP 8, enforced with Ruff (lint + format). A reasonable rule set:
  `E, W, F, I, UP, B, C4, SIM, RUF`, `line-length = 88`.
- Run the linter, the formatter and the type checker before considering a change done.
- Register every first-party package in the linter's isort `known-first-party`.

## Typing

- Explicit type hints on every public function and method. No implicit `Any`.
- Domain models are Pydantic classes; ORM models use SQLAlchemy 2.0 style
  (`Mapped[...]`, `mapped_column`).
- Use **mypy** as the type checker, with the `pydantic.mypy` plugin, `strict = True`
  for new packages. Legacy packages can be added to the checked set once clean.
- Let types carry domain distinctions the checker can enforce. When two kinds of id
  would both be a bare `int` and could be confused (e.g. ids from different tables),
  take the typed entity (`KanjiCollection`) instead of the id. mypy is nominal, so two
  subclasses with identical fields are still distinct types.
- Don't spread `**dict` into typed calls like `relationship(...)`: mypy can't check
  them. Wrap them in a small typed helper instead.

## Naming

A module's name states its role on its own, without relying on its folder.

- **Module: `<subject>_<role>.py`.** `<subject>` is the snake_case aggregate (the class
  name without its role suffix: `PracticeKanjiRepository` → `practice_kanji`). `<role>`
  is singular when the file holds one thing of that kind, plural when it holds a set
  (`commands`, `queries`, `routes`, `schemas`).
- **Package/folder: plural.** It's a namespace holding many modules. Each package
  re-exports its public names from `__init__.py` via `__all__`, so callers import from
  the package.
- **Class: singular.** Entities are unsuffixed (`PracticeEntry`, not
  `PracticeEntryEntity`); everything else carries its role (`UserRepository`,
  `UserORM`). Concrete implementations are prefixed with their library
  (`SqlAlchemyPracticeKanjiRepository`), not the database engine.
- **Spell the role out** (`_repository`, not `_repo`): it matches the class name and
  is greppable.
- **Tests: `test_<subject>_<role>.py`**, one per module under test.

| Role | Folder | Module (example) | Contents (example) |
|---|---|---|---|
| Entity | `domain/entities/` | `practice_entry_entity.py` | `PracticeEntry` + its value objects |
| Repository port | `domain/repositories/` | `practice_entry_repository.py` | `PracticeEntryRepository` |
| Domain service | `domain/services/` | `collection_service.py` | pure rules, e.g. `ensure_combinable` |
| Use cases | `application/commands/`, `application/queries/` | `collection_commands.py` | one function/class per use case |
| ORM model | `infrastructure/db/orm/` | `practice_entry_orm.py` | `PracticeEntryORM` (+ its link tables) |
| Mapper | `infrastructure/db/mappers/` | `practice_entry_mapper.py` | `practice_entry_to_domain`, `practice_entry_to_db` |
| Concrete repository | `infrastructure/repositories/` | `sqlalchemy_practice_entry_repository.py` | `SqlAlchemyPracticeEntryRepository` |
| API routes / schemas | `api/routes/`, `api/schemas/` | `collection_routes.py` | routers, request/response models |
| Test | `tests/<package>/<layer>/` | `test_collection_service.py` | `test_*` functions |

Cross-cutting single modules (`domain/exceptions.py`, `domain/clock.py`,
`api/deps.py`, `api/app.py`) stay single until they grow enough to split. A scaffold
module that is only a docstring becomes a package following the table when it gets its
first real content.

## Layers (clean architecture)

- `domain/`: entities, repository ports, pure business rules (`services/`),
  exceptions, clock. Imports nothing from the other layers.
- `application/`: use cases. Commands write and queries read. They orchestrate domain
  objects through ports, own the transaction boundary, and know nothing about the web
  framework or the ORM.
- `infrastructure/`: ORM models, mappers, concrete repositories, migrations, database
  connection.
- `api/`: routes, request/response schemas, dependency wiring (`deps.py`).

Dependencies: `api` → `application` → `domain`. `infrastructure` implements `domain`
ports and is wired in at the `api` layer (e.g. FastAPI `Depends`).

## Entities and aggregates

- **One file per aggregate root**: the root plus its nested value objects. Not one
  file per class, and not a catch-all `entities.py`.
  - Example: `practice_entry_entity.py` holds `PracticeEntry` plus `PracticeReading`,
    `PracticeSense`, `PracticeGloss`.
  - Example: `collection_entity.py` holds a `Collection` base and its
    `EntryCollection` / `KanjiCollection` subclasses.
- **Prefer subclasses over a `kind` discriminator** when the kinds have different data
  or storage: the type then tells callers what they hold.
- **Aggregates change only through their own methods** (`collection.rename(...)`,
  `entry.deactivate()`). Use cases call methods; they don't assign fields of a loaded
  aggregate.
- **Timestamps belong to the domain.** A `TimestampedEntity` base gives
  `created_at` / `updated_at` defaulting to `utc_now()` and a `touch()` method.
  **Every method that changes state calls `touch()`**; a call that changes nothing
  doesn't. Enable `validate_assignment` so methods get the same validation as the
  constructor.
- Relationships that live in link tables (e.g. collection membership) aren't fields on
  the entity. They're read and changed through repository methods.

## Repositories: ports and implementations

**Ports** (`domain/repositories/<entity>_repository.py`, one per file):

- Choose the interface style by context:
  - **`Protocol`** (default): structural typing. Implementations needn't import the
    domain, and mypy checks conformance where the object is used.
  - **`ABC`**: when a missing method must fail at instantiation (runtime enforcement),
    when implementations share concrete helpers, or when `isinstance` checks are needed.
- Methods that act on a related aggregate take the typed entity, not a bare id (see
  Typing).

**Implementations** (`infrastructure/repositories/<lib>_<entity>_repository.py`):

- Inherit the Protocol explicitly (`class SqlAlchemyXRepository(XRepository)`), so mypy
  checks conformance at the definition.
- Receive a `Session` in `__init__`, `flush()` to get ids and surface constraint
  errors, and **never commit**. The use case or request that opened the session owns
  the transaction, so several repositories share one unit of work.
- **Scope every query to the owner** (e.g. `user_id`), directly or through a parent.
- `update(entity)`: check that the stored row exists and belongs to the same owner
  (else a domain `EntityNotFoundError`), then `session.merge(<entity>_to_db(entity))`.
  Children with an id are updated, those with `id=None` inserted, and missing ones
  deleted (`delete-orphan`).
- Load nested aggregates eagerly (`selectinload`, one query per level) to avoid N+1.
- Link-table operations (add/remove membership, list by group, distinct ids across
  groups) are explicit queries: pagination, ordering and set operations belong in SQL.
  Make add/remove idempotent.
- Keep near-identical repositories as separate explicit classes until a third case
  shows what to abstract.

## Mappers

One mapper module per aggregate (`infrastructure/db/mappers/<entity>_mapper.py`), next
to the ORM models:

- `<entity>_to_domain(row: XxxORM) -> Xxx`: ORM row to domain model.
- `<entity>_to_db(entity: Xxx) -> XxxORM`: domain model to a detached ORM row. It keeps
  ids so `merge` can update. Required for any write path.
- A list's order in the domain becomes a `position` column.
- Narrow DB strings back to domain `Literal` types explicitly, and raise on unknown
  values.

## Persistence

- **One `Base`** with a `MetaData(naming_convention=...)` (`pk`, `fk`, `uq`, `ck`, `ix`)
  so every constraint has a stable name for migrations.
- If tests run on a different engine than production (e.g. SQLite vs PostgreSQL), use
  only portable column types (`JSON`, not `JSONB`) and portable SQL.
- Owned children: FK with `ondelete="CASCADE"` plus relationship
  `cascade="all, delete-orphan"`, `passive_deletes=True`, `order_by` a `position`
  column.
- Enum-like strings: `String` plus a named `CheckConstraint`, rather than a DB enum type.
- Link tables: plain `Table` objects with a composite PK, both FKs cascading, and an
  index on the item side.
- Non-time defaults (flags, statuses) go both on the ORM (`default=`) and in the
  database (`server_default=`).

### Dates and "now"

- **Naive UTC in the database, aware UTC in the backend, ISO 8601 with offset in the
  API.** Use a `TypeDecorator` over `DateTime(timezone=False)` that converts to UTC and
  strips the zone on write, attaches UTC on read, and rejects naive datetimes.
- **The domain decides "now"** through a single `utc_now()` in the domain. Timestamp
  columns get no ORM `default` / `onupdate` and no `server_default`, so a missing value
  fails instead of being invented by persistence. Rows with no entity behind them
  (e.g. `added_at` on link rows) are stamped by the repository with the domain clock.
- Database defaults for timestamps only pay off when something writes without going
  through the app. Then add them as a safety net, keeping the domain as the source.
  On a naive column in PostgreSQL that means `timezone('utc', now())`;
  `CURRENT_TIMESTAMP` would store the server's local time.

### Migrations (Alembic)

- Every model change ships with a migration in the same commit. Autogenerate against
  the real target engine, then review the file by hand.
- `env.py` reads the URL from the environment (no credentials in code), uses
  `compare_type=True`, `render_as_batch` on SQLite, and a `render_item` hook that
  renders custom types (`TypeDecorator`s) as their plain SQLAlchemy type, so
  migrations never import application code.
- Keep a **drift test**: upgrade an empty database to `head`, then assert
  `compare_metadata` against the models is empty. Also run upgrade/downgrade in CI
  against the real engine.
- Never edit a migration that has been pushed or applied anywhere shared. Add a new
  one instead.

### Configuration

- The database URL comes only from an environment variable. There is no default with
  credentials, and a missing value raises a clear error.
- Infrastructure modules read the process environment only. Loading env files is the
  launcher's job.
- Document every variable in a tracked `.env.example` with placeholder values. Real
  values live in gitignored env files or the deployment's secret settings.

## Testing

- **A real database, not mocks.** Never mock the repository or the ORM. Use in-memory
  SQLite with `StaticPool` (so every session shares one in-memory DB) and
  `PRAGMA foreign_keys = ON` (SQLite ignores FKs and cascades otherwise).
- One test file per module under test (`test_<subject>_<role>.py`). Use plain pytest
  functions and assert on domain objects returned by real calls.
- Mapper tests: `to_domain(to_db(entity)) == entity`, no database needed.
- Repository tests go through the port: owner scoping, updates of nested items,
  idempotent membership, constraint errors.
- Shared domain factories live in a local helper module. ORM rows built directly must
  pass their timestamps explicitly.

## Async: a maturity ladder, not a default

Start synchronous. Introduce `async def` routes and repositories (`AsyncSession`,
`create_async_engine`) only after agreeing it with the developer, and only for a proven
need (real concurrent load, genuinely IO-bound waits).

## Maintainability

- Avoid catch-all modules. Prefer simple composition over premature abstraction.
- Three similar lines are fine. Don't introduce an abstraction until a third real
  repetition shows what it should look like.

## Documentation

- **Document on the fly.** A change that adds or alters architecture, entities, ports,
  schema, migrations, configuration or conventions updates the matching technical doc
  in the same commit.
- Keep technical docs split by layer (architecture, domain, infrastructure,
  cross-cutting, testing), plus a **decision log**. Record non-obvious choices there,
  and add a new entry when one is reversed instead of editing the old one.
- Write functional docs per feature once its use cases are defined.
- The project's `CLAUDE.md` says where the docs live and which page maps to which code
  area.
