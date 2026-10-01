# Repository and Gateway Ports

[← Technical documentation](../README.md)

The contracts the domain depends on, all `typing.Protocol`s, one per file:

- **Repositories** (`src/shodoukan_practice/domain/repositories/`): persistence of
  practice data, implemented in
  [infrastructure/repositories](../infrastructure/repositories.md).
- **Gateways** (`src/shodoukan_practice/domain/gateways/`): read-only external
  sources, implemented in [infrastructure/dictionary](../infrastructure/dictionary-gateway.md).

## Contract shared by all ports

- Every read is scoped to a user: methods take a `user_id` (a `UUID`), or an entity
  that carries it.
- Methods that act on a collection take the **typed collection entity**
  (`EntryCollection` / `KanjiCollection`), never a bare id. Entry and kanji collection
  ids come from different tables and can collide, and mypy rejects passing the wrong
  kind. See [decisions](../decisions.md#ports-take-typed-entities-not-ids).
- `get` returns `None` when the item doesn't exist *or* belongs to someone else.
- `update` raises `EntityNotFoundError` for a missing or foreign item.

## `UserRepository`

| Method | Returns |
|---|---|
| `get(user_id)` | `User \| None` (`user_id` is the identity provider's user id, a UUID) |
| `add(user)` | the stored `User` (with id) |
| `add_if_absent(user)` | `(stored user, created)`: stores it unless a user with the same id exists; safe against concurrent first requests |

## `PracticeEntryRepository` / `PracticeKanjiRepository`

| Method | Returns / behavior |
|---|---|
| `get(id, user_id)` | the item or `None` |
| `get_many(ids, user_id)` | the user's items among `ids`, ordered by id |
| `list_by_collection(collection, limit, offset)` | active items in the collection, in the order they were added, paginated |
| `get_by_source_entry_id(source_entry_id, user_id)` / `get_by_literal(literal, user_id)` | the user's copy of that dictionary item, or `None` |
| `practice_ids_by_source_entry_id(source_entry_ids, user_id)` / `practice_ids_by_literal(literals, user_id)` | `{source_entry_id or literal: practice id}` for the ones the user has imported; reads two columns, no snapshot |
| `add(item)` | the stored item, with ids for it and every nested part |
| `add_if_absent(item)` | `(stored item, created)`: stores it unless the user already has it, and is safe against a concurrent import of the same item |
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

## `DictionaryGateway`

Read-only access to the shodoukan dictionary. It returns **fresh practice entities**
(not stored, ids `None`) so the domain never depends on the dictionary's models.

| Method | Returns |
|---|---|
| `new_practice_entry(source_entry_id, user_id)` | a `PracticeEntry` snapshot of the dictionary entry, or `None` if it doesn't exist |
| `new_practice_kanji(literal, user_id)` | a `PracticeKanji` snapshot of the dictionary kanji, or `None` |
| `search(query, lang, limit, offset)` | `DictionarySearchResult`: a page of `DictionaryEntry`s and the related `DictionaryKanji`s |

The `Dictionary*` read models (`DictionaryEntry`, `DictionarySense`, `DictionaryGloss`,
`DictionaryKanji`, `DictionaryEntryPage`, `DictionarySearchResult`, ...) are defined
with the port in `dictionary_gateway.py`. They're the practice app's own contract for
showing dictionary data: frozen, with no practice state and no `shodoukan` types.
