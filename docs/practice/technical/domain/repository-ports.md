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
| `find(user_id, search, scope, limit, offset)` | the user's items matching a [`LibrarySearch`](#library-search-domainsearches) within a scope, best match first, then the scope's order; paginated. Without text, only the scope and `active` filter |
| `count(user_id, search, scope)` | how many items `find` pages through |
| `get_by_source_entry_id(source_entry_id, user_id)` / `get_by_literal(literal, user_id)` | the user's copy of that dictionary item, or `None` |
| `practice_ids_by_source_entry_id(source_entry_ids, user_id)` / `practice_ids_by_literal(literals, user_id)` | `{source_entry_id or literal: practice id}` for the ones the user has imported; reads two columns, no snapshot |
| `add(item)` | the stored item, with ids for it and every nested part |
| `add_if_absent(item)` | `(stored item, created)`: stores it unless the user already has it, and is safe against a concurrent import of the same item |
| `update(item)` | the stored item. Replaces the whole snapshot: nested parts with an id are updated, those without one are inserted, missing ones are deleted |
| `delete(item)` | removes it from the library with its nested parts and collection links; `EntityNotFoundError` if it isn't stored for its user |

## Library search (`domain/searches/`)

The values `find` / `count` take. Built by the search use cases from what the user
typed; run by the item repositories.

- `LibrarySearch(text, kana, meaning_lang, active)`: `text` trimmed and lower-cased
  (`None` = no text filter); `kana` its `KanaForms` when it reads as romaji or kana;
  `meaning_lang` as the items store it (`eng` for entry glosses, `en` for kanji;
  `None` = any); `active` as in the library filter. `needles` are the forms looked for
  in spellings and readings (the text and its kana forms, without repeats).
- `MatchTier`: `EXACT` (3) a spelling, reading or meaning is the query; `PREFIX` (2) a
  spelling or reading starts with it, or a word of a meaning does; `CONTAINS` (1)
  anywhere. A better tier always ranks first.
- Scopes, generic over the collection type so entry and kanji ones can't mix:
  `WholeLibrary()` (most recently imported first), `InCollection(collection)` (its
  items, in the order they were added), `NotInCollection(collection)` (the library
  minus its items, for adding to it).

Readings and meanings match whether they're enabled or not: hiding is for practice,
and the user still needs to find the item to manage it.

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
| `add(collection)` / `update(collection)` | the stored collection; `CollectionNameTakenError` if the user already has a collection of that kind with that name |
| `delete(collection)` | removes the collection and its links; the items stay |

## `ExerciseRepository`

| Method | Returns / behavior |
|---|---|
| `get(id, user_id)` | the exercise (an `EntryExercise` or `KanjiExercise`) or `None` |
| `list_for_user(user_id)` | the user's exercises, by name |
| `add(exercise)` | the stored exercise, with its id |
| `update(exercise)` | replaces its fields and collections; `EntityNotFoundError` if missing or another user's |
| `delete(exercise)` | removes the exercise and its collection links; the collections stay |

## `ExerciseSessionRepository`

| Method | Returns / behavior |
|---|---|
| `get(id, user_id)` | the session with its questions, or `None` |
| `add(session)` | the stored session; its questions get their ids |
| `update(session)` | stores the answers given; `EntityNotFoundError` if missing or another user's |

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

## `KanaGateway`

Turns what the user types into kana, for searching the library by reading
(`kana_gateway.py`).

| Method | Returns |
|---|---|
| `kana_forms(text)` | `KanaForms(hiragana, katakana)` when `text` is romaji (`taberu` → たべる / タベル) or kana (`パン` → ぱん / パン); `None` otherwise (English words with letters that aren't romaji, kanji, digits) |

Both scripts because readings are stored in hiragana (kun-readings, most words) and
katakana (on-readings, loanwords).
