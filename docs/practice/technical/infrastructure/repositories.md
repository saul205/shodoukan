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

## Searching the library

`find` / `count` build one query (`_search`) shared by both, so the total always
matches the pages:

1. The user's items, with `is_active` when the search has `active`.
2. The scope: `InCollection` joins the link table and orders by `added_at, id`;
   `NotInCollection` adds `NOT EXISTS` on the link table; the whole library orders by
   `created_at DESC, id DESC`.
3. With text, a `matches` subquery of `(item_id, tier)` is joined and `tier DESC` goes
   first in the order. It's a `UNION ALL` of one SELECT per place a query can match,
   each already scoped to the user, grouped by item with `MAX(tier)`
   (`sqlalchemy_library_search.py`):
   - entries: spellings and readings against the needles (`text_match`), glosses
     against the text (`meaning_match`, in `meaning_lang` when given);
   - kanji: the literal (`EXACT` when it's the query, `PREFIX` when the query contains
     it: 兄弟 finds 兄 and 弟), readings without the okurigana dot and affix dash
     (`た.べる` → `たべる`), and meanings.

Comparisons use `lower()` and `LIKE` with `autoescape`, so `%` and `_` in the query
are literal. It's portable SQL (SQLite in tests, PostgreSQL in production). There's no
text index: the query is bounded by `user_id` and the per-item indexes; see
[decisions](../decisions.md#library-search-is-sql-over-the-normalized-snapshot).

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

## `delete(item)`

Checks the row belongs to the item's user (else `EntityNotFoundError`, like `update`)
and deletes it. Nested rows go through the ORM cascade, and the database's
`ON DELETE CASCADE` removes the collection links, so the collections stay and just lose
the item.

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

## Customising an item

Edits go through `update`: the use case loads the item, the domain changes it, and
`merge` writes the whole snapshot. A meaning added by the user has no id, so it's
inserted; one removed from the list is deleted (`delete-orphan`). The response carries
the new ids.

## Collection membership

Membership is read and written directly on the link tables:

- `add_item` checks `item.user_id == collection.user_id`, skips the insert if the
  link exists, and stamps `added_at = utc_now()`.
- `remove_item` deletes the link if present.
- A collection's items are read through the item repositories' `find` / `count` with
  `InCollection` (see [Searching the library](#searching-the-library)).
- `item_ids` returns `SELECT DISTINCT` item ids of active items across the given
  collections.
- `list_for_item` joins the link table to return an item's collections by name.
- `delete(collection)` deletes the collection row; the FK cascade removes its links.

The entry and kanji collection repositories are near-identical on purpose. There's no
shared generic base until a third collection kind shows what to abstract.

## Exercises

`SqlAlchemyExerciseRepository` loads an exercise with both link tables
(`selectinload`) and maps the one of its kind. The collection links are child rows of
the exercise, so `update` replaces them through `merge` like any nested item: links
with the same `(exercise_id, collection_id)` are updated (their `position`), new ones
inserted, missing ones deleted. `update` and `delete` check that the stored exercise
belongs to the same user (`EntityNotFoundError` otherwise). A deleted collection drops
out of its exercises through the FK cascade, with no repository code.

## Exercise sessions

`SqlAlchemyExerciseSessionRepository` loads a session with its questions
(`selectinload`); the mapper splits them into the active one (no answer) and the
history. `add` inserts the session and its first question in one flush; `update`
merges the session: answered questions are updated in place (they keep their ids), a
new active question is inserted, and one dropped by `finish` is deleted
(`delete-orphan`). `list_open` filters on `finished_at IS NULL`.
Removing an item or an exercise sets the questions' and sessions' references to NULL
in the database (`SET NULL`), with no repository code.

Writes to a session are serialized. `get_for_update` reads it with
`SELECT ... FOR UPDATE` on the session row, so a concurrent answer or finish waits for
the first transaction and then reads what it stored (SQLite, used in tests, has no
row locks). As a backstop, `UNIQUE(session_id, position)` on `exercise_questions`
stops two writers from storing the same next question: `update` flushes in a
savepoint and turns that violation into `QuestionNotActiveError`, re-raising any other
`IntegrityError`.
