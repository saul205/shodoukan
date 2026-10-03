# SQLAlchemy Repositories

[← Technical documentation](../README.md)

The implementations of the [repository ports](../domain/repository-ports.md). Code:
`src/shodoukan_practice/infrastructure/repositories/`, one class per port.

| Module | Class | Implements |
|---|---|---|
| `sqlalchemy_user_repository.py` | `SqlAlchemyUserRepository` | `UserRepository` |
| `sqlalchemy_practice_entry_repository.py` | `SqlAlchemyPracticeEntryRepository` | `PracticeEntryRepository` |
| `sqlalchemy_practice_kanji_repository.py` | `SqlAlchemyPracticeKanjiRepository` | `PracticeKanjiRepository` |
| `sqlalchemy_entry_collection_repository.py` | `SqlAlchemyEntryCollectionRepository` | `EntryCollectionRepository` |
| `sqlalchemy_kanji_collection_repository.py` | `SqlAlchemyKanjiCollectionRepository` | `KanjiCollectionRepository` |

Each class inherits its Protocol explicitly, so mypy checks it at the class
definition. The prefix names the library, not the engine: the same code runs on
PostgreSQL and on SQLite in tests.

## Transactions

Repositories receive a `Session` in `__init__`. They `flush()` to get ids and surface
constraint errors, and **never `commit()`**. The use case or request that opened the
session owns the transaction, so several repositories can share one unit of work, and
a failure rolls everything back.

## Owner scoping

Every query filters by the owning user, directly (`user_id == ...`) or through the
collection's owner. Reading another user's item returns `None`.

## Loading

The nested snapshot is loaded eagerly with `selectinload`, one query per level
(entry → readings, senses → glosses, examples → sentences), so lists don't trigger
N+1 queries.

## Listing the library

`list_for_user` and `count_for_user` share one filter (`user_id`, plus `is_active` when
`active` is given). The list loads the snapshot eagerly like every read and orders by
`created_at DESC, id DESC`, so items imported at the same instant still have a stable
order. The count is a `SELECT count(*)` that loads no snapshot.

## `update(entity)`

1. Load the stored row by id. If it doesn't exist or its `user_id` differs from the
   entity's, raise `EntityNotFoundError`. An update can never move a row to another
   user.
2. `session.merge(<entity>_to_db(entity))`: nested rows with an id are updated, rows
   with `id=None` are inserted, and stored rows missing from the entity are deleted
   (`delete-orphan`).
3. Flush and return the mapped result.

`updated_at` is whatever the entity carries: the domain bumps it with `touch()` (see
[entities](../domain/entities.md#timestamps-and-touch)).

## `add_if_absent`

Used by imports and by `EnsureUser` (users, keyed by their primary key, the provider's UUID). It inserts inside a **savepoint** (`session.begin_nested()`). If the
user's unique constraint fires (`UNIQUE(user_id, source_entry_id)` or
`UNIQUE(user_id, literal)`), meaning a concurrent request just imported the same item,
only the savepoint is rolled back. The existing copy is read and returned with
`created=False`, and the rest of the transaction is unaffected.

## Collection names

`UNIQUE(user_id, name)` on each collection table is the check for duplicate names.
Collection `add` and `update` flush inside a **savepoint**; on an `IntegrityError` they
look for another collection of the user with that name and, if there is one, raise
`CollectionNameTakenError` (anything else is re-raised). Only the savepoint is rolled
back, so the session stays usable. Why: [decisions](../decisions.md#collection-name-clashes-come-from-the-unique-constraint).

## Collection membership

Membership is read and written directly on the link tables:

- `add_item` checks `item.user_id == collection.user_id`, skips the insert if the
  link exists, and stamps `added_at = utc_now()`.
- `remove_item` deletes the link if present.
- `list_by_collection` (on the item repositories) joins the link table, keeps active
  items only, orders by `added_at, id`, and applies `LIMIT/OFFSET` in SQL.
- `item_ids` returns `SELECT DISTINCT` item ids of active items across the given
  collections.
- `list_for_item` joins the link table to return an item's collections by name.
- `delete(collection)` deletes the collection row; the FK cascade removes its links.

The entry and kanji collection repositories are near-identical on purpose. There's no
shared generic base until a third collection kind shows what to abstract.
