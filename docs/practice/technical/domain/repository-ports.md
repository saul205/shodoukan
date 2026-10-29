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

`lock(user_id)` locks the user's row for the transaction, to serialize changes that
span several of their rows (starting an exercise session).

| Method | Returns |
|---|---|
| `get(user_id)` | `User \| None` (`user_id` is the identity provider's user id, a UUID) |
| `add(user)` | the stored `User` (with id) |
| `add_if_absent(user)` | `(stored user, created)`: stores it unless a user with the same id exists; safe against concurrent first requests |
| `update(user)` | the stored `User`; `EntityNotFoundError` if it isn't stored |

## `PracticeEntryRepository` / `PracticeKanjiRepository`

| Method | Returns / behavior |
|---|---|
| `get(id, user_id)` | the item or `None` |
| `get_many(ids, user_id)` | the user's items among `ids`, ordered by id |
| `study_texts(ids, user_id, meaning_lang)` | `EntryStudyText` / `KanjiStudyText` of the user's items among `ids`, ordered by id: only what an exercise studies (see below); reads columns, no snapshot |
| `find(user_id, search, scope, limit, offset)` | the user's items matching a [`LibrarySearch`](#library-search-domainsearches) within a scope, best match first, then the scope's order; paginated. Without text, only the scope and `active` filter |
| `count(user_id, search, scope)` | how many items `find` pages through |
| `get_by_source_entry_id(source_entry_id, user_id)` / `get_by_literal(literal, user_id)` | the user's copy of that dictionary item, or `None` |
| `practice_ids_by_source_entry_id(source_entry_ids, user_id)` / `practice_ids_by_literal(literals, user_id)` | `{source_entry_id or literal: practice id}` for the ones the user has imported; reads two columns, no snapshot |
| `ids_by_form(forms, user_id)` (entries) | `{form: entry ids}` for the user's entries with an enabled spelling or reading among `forms`, as written: which library words a sentence's word may be |
| `find_own_by_identity(identities, user_id)` (entries) | the user's own words (no source) whose identity (`original_id`, or `id` for an original) is in `identities`, ordered by id: what a shared word of someone's own may already be in the library |
| `add(item)` | the stored item, with ids for it and every nested part |
| `add_if_absent(item)` | `(stored item, created)`: stores it unless the user already has it, and is safe against a concurrent import of the same item |
| `update(item)` | the stored item. Replaces the whole snapshot: nested parts with an id are updated, those without one are inserted, missing ones are deleted |
| `delete(item)` | removes it from the library with its nested parts and collection links; `EntityNotFoundError` if it isn't stored for its user |

`EntryStudyText(id, spellings, readings, sense_glosses)` and
`KanjiStudyText(id, literal, onyomi, kunyomi, meanings)` are frozen read models
defined with their port. They hold the enabled parts only, in order, with meanings in
`meaning_lang`: an entry's `sense_glosses` are the enabled glosses in that language of
each enabled sense that has any. An exercise's pool is read through them
([decision](../decisions.md#an-exercises-pool-reads-a-study-read-model)).

## `PracticeSentenceRepository`

The sentences of the user's library (`practice_sentence_repository.py`).

| Method | Returns / behavior |
|---|---|
| `get(id, user_id)` | the sentence or `None` |
| `for_entry(entry_id, user_id)` | the user's sentences with a word linked to that entry, oldest first: "the sentences of a word" |
| `find(user_id, search, limit, offset)` / `count(user_id, search)` | the user's sentences matching a `SentenceSearch(text, entry_id, linked, active)`, newest first, paginated: `text` in the sentence or a translation (any case, as typed), `entry_id` the sentences of a word, `linked=False` those with no linked word |
| `imported_by_text(texts, user_id)` | `{text: sentence}` for the user's dictionary sentences among `texts` (the oldest if two have the same text): importing a word reuses a sentence another word brought |
| `needing_analysis(user_id)` | sentences with a word to analyze: a gap not analyzed yet, or a linked word without a span |
| `users_needing_analysis()` | the users with such sentences; the one query across users, for `analyze-sentences`, which then goes user by user |
| `add(sentence)` | the stored sentence, with ids for its words |
| `update(sentence)` | the stored sentence: words with an id updated, without one inserted, missing ones deleted; translations rewritten. `EntityNotFoundError` if it isn't stored for its user |
| `delete(sentence)` | removes it, with its translations and words |

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
| `add_item(collection, item, from_source=False)` | links the item; no-op if already linked; `CollectionOwnershipError` if the item belongs to another user. `from_source`: an import from the collection's source put it there |
| `remove_item(collection, item)` | unlinks the item; no-op if not linked |
| `item_ids(collections)` | distinct ids of the **active** items across the collections |
| `add(collection)` / `update(collection)` | the stored collection; `CollectionNameTakenError` if the user already has a collection of that kind with that name |
| `delete(collection)` | removes the collection and its links; the items stay |

Sharing (the same in both):

| Method | Returns / behavior |
|---|---|
| `save_publication(collection, shared, includes_notes)` | stores the published snapshot, replacing the previous one |
| `get_publication(collection)` | the snapshot (`SharedEntryCollection` / `SharedKanjiCollection`), or `None` if never published |
| `get_public(collection_id)` | the collection if it's public, **whoever owns it** |
| `find_public(search, viewer_id, limit, offset)` / `count_public(search, viewer_id)` | public collections matching a `PublicCollectionSearch` (`domain/searches/public_collection_search.py`: `text` in the name, description or owner's username; `owner` relative to the viewer; `sort`), as `PublicCollectionSummary` |
| `public_summary(collection, viewer_id)` | one collection's summary |
| `record_download(collection, user_id, version)` | one row per user, keeping the latest version; a savepoint makes concurrent first imports safe. Downloads are counted at read time, without the owner's |

Following a source (#90):

| Method | Returns / behavior |
|---|---|
| `is_from_source(collection, item)` / `source_item_ids(collection)` | whether the source put the item there / the ids of those items |
| `dismiss_item(collection, key)` / `undismiss_item(collection, key)` / `dismissed_items(collection)` | remember the shared key of an item the user took out of a copy (idempotent) / forget it (whether it was there) / those keys |
| `latest_source_versions(user_id)` | `{copy id: source's published_version}` for the user's copies whose source is public |

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
| `get(id, user_id)` | the session with its active question and history, or `None` |
| `get_for_update(id, user_id)` | `get`, locking the session until the transaction ends; used by the use cases that change it |
| `list_open(user_id)` | the user's sessions with no `finished_at` (one at most, normally), locked for the transaction |
| `list_summaries(user_id, now, *, exercise_id, status, limit, offset)` | the history: `SessionSummary`s, newest first, optionally of one exercise and only `"open"` or `"finished"` at `now` (idle ones count as finished); paginated |
| `count_summaries(user_id, now, *, exercise_id, status)` | how many sessions `list_summaries` pages through |
| `add(session)` | the stored session; its questions get their ids; `SessionAlreadyOpenError` if the user has another open session |
| `update(session)` | stores answers, the new active question and the state; a dropped active question is deleted; `EntityNotFoundError` if missing or another user's; `QuestionNotActiveError` if another request stored the next question first |

`SessionSummary` is a frozen read model defined with the port: a session without its
questions (`id`, `exercise_id`, `exercise_name`, `item_kind`, `started_at`,
`last_activity_at`, `finished_at` as stored, `answered`, `score`). Its `ended_at(now)`
applies the same idle rule as `ExerciseSession.ended_at` (`session_end`). Why read
models come from ports: [decisions](../decisions.md#read-models-for-history-and-statistics-come-from-ports).

## `ExerciseStatisticsRepository`

Read-only aggregates over the answered questions of the user's sessions
(`exercise_statistics_repository.py`). Sessions are the statistics: nothing is
stored twice, every figure is computed when asked. Methods taking an optional
`exercise: Exercise` are scoped to it; without it, to every session of the user.

| Method | Returns |
|---|---|
| `totals(user_id, exercise)` | `AnswerTotals(sessions, answered, correct, mean_response_ms)`; `sessions` counts those with at least one answer |
| `by_direction(user_id, exercise)` | `DirectionTotals(prompt_fields, answer_field, answered, correct)` per direction, most answered first |
| `most_missed_entries(user_id, exercise, limit)` / `most_missed_kanji(...)` | `ItemTotals(item_id, answered, wrong)` for items answered wrong at least once, most misses first (then fewest answers); questions whose item left the library don't count |
| `by_exercise(user_id)` | `ExerciseTotals(exercise_id, exercise_name, item_kind, sessions, answered, correct, last_answered_at)` per exercise with answers, most recently answered first, under its current name; deleted exercises are left out |
| `answers_since(user_id, since)` | `AnswerMoment(answered_at, is_correct)` for each answer since `since`, oldest first |

The read models are frozen and defined with the port. `DirectionTotals.prompt_fields`
is a `frozenset`: a direction is the same whatever the order of its shown fields. The
most missed are split per item kind so entry and kanji ids can't mix (see
[decisions](../decisions.md#directions-are-grouped-as-sets-most-missed-is-split-per-kind)).

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

## `MorphologyGateway`

Splits a Japanese sentence into morphemes (`morphology_gateway.py`). Sentences use it
when they're added or edited, to propose their words, link them to the library and
know the form of a gap; the morphemes aren't stored
([proposal](../../proposals/sentences.md)).

| Method | Returns |
|---|---|
| `morphemes(text)` | The `Morpheme`s of `text`, in order, covering all of it |

`Morpheme` (a `NamedTuple`): `surface`; `lemma`, the dictionary form (引く for 引か);
`reading`, of the surface, in katakana; `pos`, the part of speech, most general first
(`("動詞", "一般")`); `conjugation_type` and `conjugation_form` (活用型 and 活用形,
`"五段-カ行"`, `"未然形-一般"`; `None` when it doesn't inflect); `start` and `end`,
character offsets in `text`.

Implemented by `SudachiMorphologyGateway`: see
[morphology gateway](../infrastructure/morphology-gateway.md).
