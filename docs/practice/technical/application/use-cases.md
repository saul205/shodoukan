# Use Cases

[← Technical documentation](../README.md)

The application layer: what each use case does, with which ports. Code:
`src/shodoukan_practice/application/` (`commands/` write, `queries/` read).

Use cases receive their ports in `__init__` and expose `execute(...)`. They never
commit: the caller (the API route) owns the transaction. See
[endpoints](../api/endpoints.md#transactions).

## Commands (`commands/library_commands.py`)

### `ImportEntry(dictionary, entries).execute(user_id, source_entry_id)`

Copies dictionary entry `source_entry_id` into the user's library.

1. If the user already has it (`entries.get_by_source_entry_id`), return it with
   `created=False`. Nothing is written, and the dictionary isn't read.
2. Otherwise ask the [dictionary gateway](../infrastructure/dictionary-gateway.md) for
   a fresh snapshot. If there's none, raise `DictionaryItemNotFoundError`.
3. Store it with `entries.add_if_absent`. If a concurrent request stored the same item
   in between, that copy is returned with `created=False`. See
   [repositories](../infrastructure/repositories.md#add_if_absent).

Returns `ImportResult[PracticeEntry]` (`item`, `created`).

### `ImportKanji(dictionary, kanji).execute(user_id, literal)`

Same flow for kanji, keyed by `literal` (`kanji.get_by_literal`,
`dictionary.new_practice_kanji`).

## Commands (`commands/collection_commands.py`)

Entry and kanji collections have their own use cases with the same behavior
(`...EntryCollection` / `...KanjiCollection`, `Add/RemoveEntry...` /
`Add/RemoveKanji...`). Collections and items are looked up with the user's id, so a
missing one and another user's one both raise `EntityNotFoundError`.

### `CreateEntryCollection(collections).execute(user_id, name, description=None)`

Stores an empty collection and returns it. `CollectionNameTakenError` if the user
already has an entry collection with that name (entry and kanji collections may share
one).

### `UpdateEntryCollection(collections).execute(user_id, collection_id, name, description)`

Replaces both editable fields through `rename` and `describe`, so `updated_at` only
moves when something changed. `EntityNotFoundError` or `CollectionNameTakenError`.
Why both at once: [decisions](../decisions.md#collection-updates-replace-name-and-description).

### `DeleteEntryCollection(collections).execute(user_id, collection_id)`

Deletes the collection and its membership links; the items stay in the library.

### `AddEntryToCollection(collections, entries).execute(user_id, collection_id, entry_id)`

Links a library entry (its practice id) to the collection. Idempotent. Kanji:
`AddKanjiToCollection(collections, kanji)`.

### `RemoveEntryFromCollection(collections, entries).execute(user_id, collection_id, entry_id)`

Unlinks it; the entry stays in the library. Idempotent, but the entry itself must
exist (else `EntityNotFoundError`).

## Commands (`commands/user_commands.py`)

### `EnsureUser(users).execute(user_id, username)`

Returns the practice user whose `id` is `user_id`, the identity provider's user id
(the token's `sub`, a UUID), **creating it** with that same id if this is the
identity's first request. `username`
(the token's `preferred_username`) is only used on creation. Creation goes through
`users.add_if_absent`, so two concurrent first requests create a single user. See
[decisions](../decisions.md#users-are-created-on-their-first-request).

## Queries (`queries/dictionary_queries.py`)

### `SearchDictionary(dictionary).execute(query, lang, limit, offset)`

Dictionary search through the [dictionary gateway](../infrastructure/dictionary-gateway.md#search).
It returns the gateway's `DictionarySearchResult` read models. It needs no user: the
results are the same for everyone, and import status is
[`GetImportStatus`](#getimportstatusentries-kanjiexecuteuser_id-source_entry_ids-literals).

## Queries (`queries/library_queries.py`)

### `GetImportStatus(entries, kanji).execute(user_id, source_entry_ids, literals)`

Which of the given dictionary items the user has imported, e.g. a page of search
results. Returns `ImportStatus(entries={source_entry_id: practice_id},
kanji={literal: practice_id})` with only the imported ones. Duplicates in the input
are ignored, and an empty input skips the query. It uses the repositories' lightweight
lookups (`practice_ids_by_source_entry_id`, `practice_ids_by_literal`), which read two
columns and load no snapshots.

### `ListLibraryEntries(entries).execute(user_id, limit, offset, active=None)`

A page of the user's imported entries, most recently imported first, as
`LibraryPage[PracticeEntry]` (`items`, `total`, `limit`, `offset`). Inactive entries
are included unless `active` is given, so the library page can show and reactivate
them. It's what the UI lists to pick items for a collection.
`ListLibraryKanji(kanji)` likewise.

## Queries (`queries/collection_queries.py`)

### `ListEntryCollections(collections).execute(user_id)`

The user's entry collections, ordered by name. `ListKanjiCollections` likewise.

### `GetEntryCollection(collections).execute(user_id, collection_id)`

One collection, or `EntityNotFoundError`. `GetKanjiCollection` likewise.

### `ListEntryCollectionItems(collections, entries).execute(user_id, collection_id, limit, offset)`

A page of the collection's **active** items, in the order they were added
(`list_by_collection`). `EntityNotFoundError` if the collection isn't the user's.
`ListKanjiCollectionItems(collections, kanji)` likewise.
