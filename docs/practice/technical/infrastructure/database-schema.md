# Database Schema

[← Technical documentation](../README.md)

Tables, constraints and cascades of the practice database. The engine is
**PostgreSQL**; unit tests run on SQLite, so only portable column types are used.
The models that define these tables are described in
[ORM and mappers](orm-and-mappers.md).

## Tables

| Table | Parent | Constraints and notes |
|---|---|---|
| `users` | — | `id` **`uuid`**: the identity provider's user id (token `sub`), not generated here; `username` (display name, up to 255 characters, not unique) |
| `practice_entries` | `users` | `UNIQUE(user_id, source_entry_id)` |
| `practice_entry_kanji_readings` | `practice_entries` | `position`, `info` JSON, `enabled` |
| `practice_entry_readings` | `practice_entries` | `position`, `info` / `restricted_to` JSON, `enabled` |
| `practice_senses` | `practice_entries` | `position`, `pos` / `misc` / `dialects` / `info` JSON |
| `practice_glosses` | `practice_senses` | `position`, `enabled`, `origin` with `CHECK origin IN ('imported','added')` |
| `practice_examples` | `practice_senses` | `position`, `enabled`, `origin` (CHECK) |
| `practice_example_sentences` | `practice_examples` | `position`, `lang`, `text` |
| `practice_kanji` | `users` | `UNIQUE(user_id, literal)` |
| `practice_kanji_reading_items` | `practice_kanji` | `kind` with `CHECK kind IN ('on','kun','nanori')`, `position`, `enabled` |
| `practice_kanji_meanings` | `practice_kanji` | `position`, `enabled`, `origin` (CHECK) |
| `entry_collections` | `users` | `UNIQUE(user_id, name)` |
| `kanji_collections` | `users` | `UNIQUE(user_id, name)` |
| `entry_collection_items` | link table | PK `(collection_id, entry_id)`, index on `entry_id`, `added_at` |
| `kanji_collection_items` | link table | PK `(collection_id, kanji_id)`, index on `kanji_id`, `added_at` |

Every table except `users` and the link tables has an integer `id` primary key.
`users.id` is a UUID, and so is every `user_id` foreign key (`practice_entries`,
`practice_kanji`, `entry_collections`, `kanji_collections`). SQLAlchemy's `Uuid` type is
native `uuid` on PostgreSQL and `CHAR(32)` on SQLite. Aggregate tables
(`users`, `practice_entries`, `practice_kanji`, `*_collections`) have `created_at` and
`updated_at`.

## Cascades

- Every foreign key uses `ON DELETE CASCADE`.
- Deleting a user removes their whole library, their collections and all links.
- Deleting an entry or kanji removes its nested rows and its links; the collections
  stay.
- Deleting a collection removes its links; the items stay.

## Conventions

- **Order.** Nested lists keep their order in a `position` column (0-based).
- **Lists of strings** are `JSON` columns (portable; not `JSONB`).
- **Dates** are `timestamp without time zone` holding UTC, with no database default.
  See [dates and time zones](../cross-cutting/dates-and-time-zones.md).
- **Other defaults** (`enabled`, `is_active` → true, `origin` → `'imported'`) are set
  both on the ORM and as `server_default`, so raw SQL inserts get them too.
- **Constraint names** are deterministic (`pk_<table>`, `fk_<table>_<col>_<ref>`,
  `uq_<table>_<cols>`, `ck_<table>_<name>`, `ix_<table>_<col>`), set by the naming
  convention on `Base`. This lets Alembic alter and drop constraints reliably.
- Enum-like strings use a named `CHECK` constraint rather than a database enum type,
  which keeps them portable and easy to extend with a migration.
