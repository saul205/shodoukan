# Use Cases

[← Technical documentation](../README.md)

The application layer: what each use case does, with which ports. Code:
`src/shodoukan_practice/application/` (`commands/` write, `queries/` read).

Use cases receive their ports in `__init__` and expose `execute(...)`. They never
commit: the caller (the API route) owns the transaction. See
[endpoints](../api/endpoints.md#transactions).

## Commands (`commands/library_commands.py`)

### `ImportEntry(dictionary, entries, collections).execute(user_id, source_entry_id, collection_ids=())`

Copies dictionary entry `source_entry_id` into the user's library and, optionally,
into some of the user's entry collections.

1. Look up every collection in `collection_ids` (duplicates ignored) scoped to the
   user. A missing one, or another user's, raises `EntityNotFoundError` before
   anything is read or written, so a failed request imports nothing.
2. If the user already has the entry (`entries.get_by_source_entry_id`), take it with
   `created=False`. The dictionary isn't read.
3. Otherwise ask the [dictionary gateway](../infrastructure/dictionary-gateway.md) for
   a fresh snapshot. If there's none, raise `DictionaryItemNotFoundError`.
4. Store it with `entries.add_if_absent`. If a concurrent request stored the same item
   in between, that copy is returned with `created=False`. See
   [repositories](../infrastructure/repositories.md#add_if_absent).
5. Add the item to each collection (`collections.add_item`, idempotent). This also
   happens when the item was already imported.

Returns `ImportResult[PracticeEntry]` (`item`, `created`). Why collections are part
of the import: [decisions](../decisions.md#importing-into-collections-is-one-request).

### `ImportKanji(dictionary, kanji, collections).execute(user_id, literal, collection_ids=())`

Same flow for kanji, keyed by `literal` (`kanji.get_by_literal`,
`dictionary.new_practice_kanji`), with kanji collections.

The collection lookups (`entry_collection`, `kanji_collection`) live in
`commands/collection_lookups.py`, shared with the collection commands below.

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

## Commands (`commands/exercise_commands.py`)

Collection ids are checked against the user's collections **of the exercise's kind**
(`entry_collection` / `kanji_collection`), so another user's collection, a missing one,
or an id that only exists among collections of the other kind raises
`EntityNotFoundError`. Duplicated ids are dropped, keeping the first. Settings that use
fields of the other kind fail the entity's validation (a Pydantic `ValidationError`,
`422` in the API).

### `CreateExercise(exercises, entry_collections, kanji_collections).execute(user_id, item_kind, name, description, collection_ids, settings)`

Builds an `EntryExercise` or a `KanjiExercise` from `item_kind` and stores it.

### `UpdateExercise(exercises, entry_collections, kanji_collections).execute(user_id, exercise_id, name, description, collection_ids, settings)`

Replaces every editable field through `rename`, `describe`, `use_collections` and
`configure`, so `updated_at` only moves when something changed. The item kind never
changes. `EntityNotFoundError` for a missing or foreign exercise.

### `DeleteExercise(exercises).execute(user_id, exercise_id)`

Deletes the exercise and its collection links; the collections stay.

## Commands (`commands/exercise_session_commands.py`)

Answering and finishing load the session with `get_for_update`, so concurrent
requests on one session (a double click) run one after the other: the second sees the
question already answered (`QuestionNotActiveError`). The three of them read the
exercise's pool the same way: the **active** items of its
collections (`item_ids`, then `get_many`), as study cards in the session's
`meaning_lang` (as the items store it: `eng` for entries, `en` for kanji). `rng`
defaults to a new `random.Random`; tests pass a seeded one.

### `StartExerciseSession(exercises, sessions, entry_collections, kanji_collections, entries, kanji, rng=None).execute(user_id, exercise_id, meaning_lang)`

Loads the exercise (`EntityNotFoundError` if missing or another user's), checks the
pool (`ExercisePoolTooSmallError` with fewer than 2 usable items, including when the
exercise has no collections left), finishes the user's open sessions of that
exercise at their last activity, and stores a new session with its first active
question.

### `AnswerExerciseQuestion(exercises, sessions, entry_collections, kanji_collections, entries, kanji, rng=None).execute(user_id, session_id, question_id, answer, response_ms=None)`

Grades the active question (`ExerciseSession.answer`), builds the next one from the history
and the current pool, and stores both. Returns the stored session, the graded question
and the next active one: `None` if the pool can't make another (the session stays
open), or if the exercise was deleted (the session is finished; the answer counts).
`EntityNotFoundError`; `SessionFinishedError` if the session is finished or idle (then
nothing is written: an answer that fails doesn't commit); `QuestionNotActiveError`
or `InvalidAnswerError`.

### `FinishExerciseSession(sessions).execute(user_id, session_id)`

Closes the session (at its last activity if it was idle) and drops its active
question. Finishing a finished session changes nothing. `EntityNotFoundError`.

## Commands (`commands/practice_entry_commands.py`, `commands/practice_kanji_commands.py`)

Customising an item of the library. Each one loads the user's item with `get(id,
user_id)` (`EntityNotFoundError` if it isn't theirs), calls one
[domain method](../domain/entities.md#customisation-rules), stores it with `update`
and returns the stored item, with ids for anything new.

| Entry | Kanji | Does |
|---|---|---|
| `SetEntryActive` | `SetKanjiActive` | `activate()` / `deactivate()` |
| `SetEntryNotes` | `SetKanjiNotes` | the general note |
| `SetSenseNotes` | — | a sense's note |
| `SetEntryPartEnabled` | `SetKanjiPartEnabled` | enable or disable one nested item |
| `AddEntryGloss` | `AddKanjiMeaning` | add a meaning of the user's own |
| `EditEntryGloss` | `EditKanjiMeaning` | change an own meaning's text (`OriginalDataError` for imported ones) |
| `RemoveEntryGloss` | `RemoveKanjiMeaning` | remove an own meaning (`OriginalDataError` for imported ones) |
| `RemoveEntryFromLibrary` | `RemoveKanjiFromLibrary` | `delete(item)`: the copy and its collection links go; returns nothing |

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

### `GetDictionaryEntry(dictionary).execute(entry_id)` / `GetDictionaryKanji(dictionary).execute(literal)`

One entry or kanji for its detail page; `DictionaryItemNotFoundError` if the dictionary
doesn't have it.

### `ListEntriesForKanji(dictionary).execute(literal, limit, offset)`

A `DictionaryEntryPage` of the words written with the kanji.
`DictionaryItemNotFoundError` if the kanji doesn't exist, so a typo isn't shown as a
kanji no word uses.

### `ListKanjiForEntry(dictionary).execute(entry_id)`

The kanji in the entry's spellings; `DictionaryItemNotFoundError` if the entry doesn't
exist.

## Queries (`queries/library_queries.py`)

### `GetImportStatus(entries, kanji).execute(user_id, source_entry_ids, literals)`

Which of the given dictionary items the user has imported, e.g. a page of search
results. Returns `ImportStatus(entries={source_entry_id: practice_id},
kanji={literal: practice_id})` with only the imported ones. Duplicates in the input
are ignored, and an empty input skips the query. It uses the repositories' lightweight
lookups (`practice_ids_by_source_entry_id`, `practice_ids_by_literal`), which read two
columns and load no snapshots.

### `GetLibraryEntry(entries).execute(user_id, entry_id)` / `GetLibraryKanji(kanji)`

One item of the user's library for its detail page; `EntityNotFoundError` if it isn't
theirs.

### `ListCollectionsOfEntry(entries, collections).execute(user_id, entry_id)` / `ListCollectionsOfKanji`

The collections (tags) the item is in, by name (`list_for_item`).

## Queries (`queries/library_search_queries.py`)

Every list of library items is a search: the library page, a collection's items and
the picker that adds items to a collection only differ in scope. See
[decisions](../decisions.md#library-search-is-one-module-over-the-item-repositories).

### `SearchEntries(entries, collections, kana).execute(user_id, text=None, meaning_lang=None, active=None, in_collection=None, not_in_collection=None, limit=20, offset=0)`

A `LibraryPage[PracticeEntry]` (`items`, `total`, `limit`, `offset`) of the user's
entries matching `text`, best match first; blank text lists the scope in its own order.

| Scope | Items | Order without text |
|---|---|---|
| neither id | the library; inactive too unless `active` is given (the library page shows and reactivates them) | most recently imported first |
| `in_collection` | the collection's items; inactive too unless `active` is given, as in the library (practice reads `item_ids`, which is active-only) | the order they were added |
| `not_in_collection` | the library minus the collection's items: what the picker can still add | most recently imported first |

The collection is loaded first (`GetEntryCollection`): `EntityNotFoundError` if it
isn't the user's. Passing both ids is a `ValueError`. `SearchKanji(kanji, collections,
kana)` likewise.

Shared helpers:

- `build_search(text, meaning_lang, active, kana)`: trims and lower-cases the text,
  adds its kana forms through `KanaGateway` (romaji → kana, both scripts) and turns
  blank text or language into `None`.
- `resolve_scope(get_collection, in_collection, not_in_collection)`: the
  `SearchScope` for the ids.

## Queries (`queries/collection_queries.py`)

### `ListEntryCollections(collections).execute(user_id)`

The user's entry collections, ordered by name. `ListKanjiCollections` likewise.

### `GetEntryCollection(collections).execute(user_id, collection_id)`

One collection, or `EntityNotFoundError`. `GetKanjiCollection` likewise.

A collection's items are listed (and searched) with
[`SearchEntries` / `SearchKanji`](#queries-querieslibrary_search_queriespy) and
`in_collection`.

## Queries (`queries/exercise_queries.py`)

### `ListExercises(exercises).execute(user_id)`

The user's exercises, by name.

### `GetExercise(exercises).execute(user_id, exercise_id)`

One exercise, or `EntityNotFoundError` if it's missing or another user's.

## Queries (`queries/exercise_session_queries.py`)

### `GetExerciseSession(sessions).execute(user_id, session_id)`

One of the user's sessions with its active question and history, or
`EntityNotFoundError`. It doesn't write: the API reports an idle session as finished
(`ended_at`) without storing it.
