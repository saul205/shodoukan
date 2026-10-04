# ORM Models and Mappers

[← Technical documentation](../README.md)

How the tables in the [schema](database-schema.md) are modelled with SQLAlchemy 2.0,
and how rows are converted to and from [domain entities](../domain/entities.md).

## ORM models (`infrastructure/db/orm/`)

One module per aggregate, all re-exported from `orm/__init__.py`. Importing the
package registers every table on `Base.metadata`, which Alembic and `create_all` use.

| Module | Models |
|---|---|
| `base_orm.py` | `Base` (naming convention), `UtcDateTime`, helpers |
| `user_orm.py` | `UserORM` |
| `practice_entry_orm.py` | `PracticeEntryORM`, `PracticeEntryKanjiReadingORM`, `PracticeEntryReadingORM`, `PracticeSenseORM`, `PracticeGlossORM`, `PracticeExampleORM`, `PracticeExampleSentenceORM` |
| `practice_kanji_orm.py` | `PracticeKanjiORM`, `PracticeKanjiReadingItemORM`, `PracticeKanjiMeaningORM` |
| `entry_collection_orm.py` | `EntryCollectionORM`, `entry_collection_items` (plain `Table`) |
| `kanji_collection_orm.py` | `KanjiCollectionORM`, `kanji_collection_items` (plain `Table`) |
| `exercise_orm.py` | `ExerciseORM`, `ExerciseEntryCollectionORM`, `ExerciseKanjiCollectionORM` (children of the exercise via `children()`) |

Helpers in `base_orm.py`:

- `children("<Model>.position")`: a one-to-many relationship to rows owned by the
  parent, ordered by `position`, with `cascade="all, delete-orphan"` and
  `passive_deletes=True` (the database FK cascade does the deleting).
- `created_at_column()` / `updated_at_column()`: `UtcDateTime` columns with no default.
- `UtcDateTime`: see [dates and time zones](../cross-cutting/dates-and-time-zones.md).
- `in_check(column, values)`: SQL for an `IN (...)` check constraint.

Link tables have **no ORM relationship** to collections or items on purpose: the
[repositories](repositories.md#collection-membership) query them explicitly.

## Mappers (`infrastructure/db/mappers/`)

One module per aggregate (`*_mapper.py`), each with two functions:

- `<entity>_to_domain(row) -> Entity`
- `<entity>_to_db(entity) -> EntityORM`: a detached row that **keeps the ids**, so
  `Session.merge` can update existing rows.

Mapping rules:

- A list's index in the domain becomes `position` in the row.
- Kanji `on_readings`, `kun_readings` and `nanori` go into one table, split by `kind`
  (`position` is the index within its kind).
- `PracticeExampleSentence` has no identity in the domain. Its rows get a fresh id on
  every update.
- An exercise's `collection_ids` become rows of the link table of its kind
  (`ExerciseEntryCollectionORM` for an `EntryExercise`, `ExerciseKanjiCollectionORM`
  for a `KanjiExercise`), with their order as `position`. `item_kind` picks the
  subclass on the way back; an unknown value raises `ValueError`.
- Exercise `settings` are dumped to JSON-compatible dicts and validated back through
  a `TypeAdapter` of `ExerciseSettings`, so a stored type picks its settings class.
- `origin` strings are narrowed back to the domain's `Literal` type. Unknown values
  raise `ValueError`, and the `CHECK` constraint prevents them anyway.
