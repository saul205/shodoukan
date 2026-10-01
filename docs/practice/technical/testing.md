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

## Fixtures and helpers

- `infrastructure/conftest.py`:
  - `engine`: `sqlite://` with `StaticPool` (every session shares the same in-memory
    database), `PRAGMA foreign_keys = ON` (SQLite ignores FKs and `ON DELETE CASCADE`
    otherwise), and `Base.metadata.create_all`;
  - `session`, `user`, `other_user`;
  - `dictionary`: a real `shodoukan.Dictionary` over a temporary SQLite, built with
    the core library's `SCHEMA` and `seed` from `tests/db_helpers.py`
    (`auto_download=False`).
- `infrastructure/factories.py`: `make_entry`, `make_kanji`, `make_entry_collection`,
  `make_kanji_collection` (domain entities), `NOW`, and `TIMESTAMPS` for ORM rows built
  directly (the database has no timestamp defaults).

## CI

`.github/workflows/ci.yml` installs the package, runs `mypy` and
`pytest tests/shodoukan-practice`, then runs the migrations against a throwaway
`postgres:16-alpine` service: `upgrade head`, `check`, `downgrade base`, `upgrade head`.
