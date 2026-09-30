# Repository Ports

[← Technical documentation](../README.md)

The persistence contracts the domain depends on. Code:
`src/shodoukan_practice/domain/repositories/`, one `typing.Protocol` per file. The
implementations are described in
[infrastructure/repositories](../infrastructure/repositories.md).

## Contract shared by all ports

- Every read is scoped to a user: methods take a `user_id`, or an entity that carries
  it.
- Methods that act on a collection take the **typed collection entity**
  (`EntryCollection` / `KanjiCollection`), never a bare id. Entry and kanji collection
  ids come from different tables and can collide, and mypy rejects passing the wrong
  kind. See [decisions](../decisions.md#ports-take-typed-entities-not-ids).
- `get` returns `None` when the item doesn't exist *or* belongs to someone else.
- `update` raises `EntityNotFoundError` for a missing or foreign item.

## `UserRepository`

| Method | Returns |
|---|---|
| `get(user_id)` | `User \| None` |
| `add(user)` | the stored `User` (with id) |

## `PracticeEntryRepository` / `PracticeKanjiRepository`

| Method | Returns / behavior |
|---|---|
| `get(id, user_id)` | the item or `None` |
| `get_many(ids, user_id)` | the user's items among `ids`, ordered by id |
| `list_by_collection(collection, limit, offset)` | active items in the collection, in the order they were added, paginated |
| `add(item)` | the stored item, with ids for it and every nested part |
| `update(item)` | the stored item. Replaces the whole snapshot: nested parts with an id are updated, those without one are inserted, missing ones are deleted |

## Collection repositories

`EntryCollectionRepository` / `KanjiCollectionRepository`:

| Method | Returns / behavior |
|---|---|
| `get(id, user_id)` | the collection or `None` |
| `list_for_user(user_id)` | the user's collections, by name |
| `list_for_item(item)` | the collections (tags) the item belongs to, by name |
| `add_item(collection, item)` | links the item; no-op if already linked; `CollectionOwnershipError` if the item belongs to another user |
| `remove_item(collection, item)` | unlinks the item; no-op if not linked |
| `item_ids(collections)` | distinct ids of the **active** items across the collections |
| `add(collection)` / `update(collection)` | the stored collection |
| `delete(collection)` | removes the collection and its links; the items stay |
