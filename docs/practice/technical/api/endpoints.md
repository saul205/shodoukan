# Endpoints

[← Technical documentation](../README.md)

The HTTP API of the practice app. Code: `src/shodoukan_practice/api/`
(`app.py`, `routes/`, `schemas/`, `deps.py`). Interactive docs at `/docs` when running.

Every endpoint except `GET /dictionary/search` requires a bearer token; see
[authentication](authentication.md). The
app runs on port **8001** (`shodoukan-api` uses 8000):
`uvicorn shodoukan_practice.api.app:app --port 8001` or `shodoukan-practice`.

## `GET /library/entries` and `GET /library/kanji`

The current user's library, one kind per route, listed or searched
([`SearchEntries` / `SearchKanji`](../application/use-cases.md#queries-querieslibrary_search_queriespy)).
It's also what the UI shows to pick items for a collection: each item's `id` is what
[`PUT /collections/.../items/{id}`](#collections) takes.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `q` | string, ≤ 100 | none | Search by spelling or reading (kanji, kana, or romaji converted to kana) and by meaning; hidden readings and meanings count. Blank lists everything |
| `meaning_lang` | string, ≤ 8 | any | Language of the meanings to search, as stored: ISO 639-2 for entries (`eng`), ISO 639-1 for kanji (`en`) |
| `active` | bool | all | `true` only active items, `false` only deactivated ones |
| `not_in_collection` | int | none | Leave out the items of this collection of the user's (the picker's "what can still be added") |
| `limit` | int, 1–100 | `20` | Items per page |
| `offset` | int, ≥ 0 | `0` | Items to skip |

| Status | When | Body |
|---|---|---|
| `200` | Always, for a valid token | `PracticeEntryPageResponse` / `PracticeKanjiPageResponse` |
| `401` | Missing or invalid token | `{"detail": ...}` |
| `404` | `not_in_collection` isn't one of the user's collections | `{"detail": ...}` |
| `422` | Out-of-range `limit` or `offset`, `q` over 100 characters | validation errors |

Without `q`, items are ordered most recently imported first. With it, best match
first (a spelling, reading or meaning equal to the query; then one starting with it,
or a meaning with a word that does; then one containing it), then newest first. The page has the same shape as the
dictionary search's entry page, with `total` counting every matching item:

```json
{ "items": [{ "id": 7, "source_entry_id": 1358280, ... }], "total": 42, "limit": 20, "offset": 0 }
```

## Library items: detail and customisation

One item of the user's library (its practice `id`). Code:
`routes/practice_entry_routes.py`, `routes/practice_kanji_routes.py`. All need a token.
**Every edit returns the whole item as it is now** (`PracticeEntryResponse` /
`PracticeKanjiResponse`), so the client re-renders from the response and gets the ids
of anything new. The rules are in
[entities](../domain/entities.md#customisation-rules): dictionary data is only ever
disabled.

| Method | Route | Body | Success |
|---|---|---|---|
| `GET` | `/library/entries/{id}` | — | `200` the entry |
| `DELETE` | `/library/entries/{id}` | — | `204`; also leaves every collection |
| `GET` | `/library/entries/{id}/collections` | — | `200` `list[CollectionResponse]`, by name |
| `PUT` | `/library/entries/{id}/active` | `{"active": false}` | `200` |
| `PUT` | `/library/entries/{id}/notes` | `{"notes": "..."}` (≤ 2000; blank or `null` removes it) | `200` |
| `PUT` | `/library/entries/{id}/senses/{sense_id}/notes` | `{"notes": "..."}` | `200` |
| `PUT` | `/library/entries/{id}/{part}/{item_id}/enabled` | `{"enabled": false}` | `200`; `part` is `kanji-readings`, `readings`, `senses`, `glosses` or `examples` (a disabled sense hides its meanings and examples, keeping their flags) |
| `POST` | `/library/entries/{id}/kanji-readings` | `{"kanji": "..."}` | `201`; a spelling of the user's own |
| `DELETE` | `/library/entries/{id}/kanji-readings/{spelling_id}` | — | `200`; `409` for a dictionary spelling |
| `POST` | `/library/entries/{id}/readings` | `{"text": "..."}` (kana) | `201`; a reading of the user's own |
| `DELETE` | `/library/entries/{id}/readings/{reading_id}` | — | `200`; `409` for a dictionary reading or the word's last one |
| `POST` | `/library/entries/{id}/senses` | `{"text": "...", "lang": "eng"}`: its first meaning | `201`; an own sense at the end |
| `DELETE` | `/library/entries/{id}/senses/{sense_id}` | — | `200`; with its meanings and examples; `409` for a dictionary sense |
| `POST` | `/library/entries/{id}/senses/{sense_id}/glosses` | `{"text": "...", "lang": "eng"}` (ISO 639-2) | `201`; `422` if `lang` isn't the sense's (a sense's meanings are in one language) |
| `PUT` | `/library/entries/{id}/glosses/{gloss_id}` | `{"text": "..."}` | `200`; `409` for a dictionary meaning |
| `DELETE` | `/library/entries/{id}/glosses/{gloss_id}` | — | `200`; `409` for a dictionary meaning or the sense's only one |
| `POST` | `/library/entries/{id}/senses/{sense_id}/examples` | `{"japanese": "...", "translation": "..." \| null, "lang": "eng"}` | `201`; an own example at the end of the sense |
| `PUT` | `/library/entries/{id}/examples/{example_id}` | same body | `200`; replaces the Japanese sentence and the translation in `lang`, keeps the others; `409` for a dictionary example |
| `DELETE` | `/library/entries/{id}/examples/{example_id}` | — | `200`; `409` for a dictionary example |

Kanji, under `/library/kanji/{id}`: the same `GET`, `DELETE`, `/collections`,
`/active` and `/notes`; `/{part}/{item_id}/enabled` with `part` `readings` (on, kun and
nanori) or `meanings`; `POST /meanings` with `{"text", "lang"}` (ISO 639-1, e.g. `en`);
`PUT` / `DELETE /meanings/{meaning_id}`.

Meaning texts are stripped and must be 1–500 characters, as must an example's Japanese
sentence; its translation is optional (≤ 500) and its `lang` can't be `jpn`. The responses carry `notes` on
the item and, for entries, on each sense, which also has `enabled` and `origin`.

| Status | When |
|---|---|
| `401` | Missing or invalid token |
| `404` | Not in the user's library (or another user's), or no such sense or nested item |
| `409` | Editing or removing a dictionary meaning or example, or removing a dictionary spelling, reading or sense, a word's last reading or a sense's last meaning |
| `422` | Unknown `part`, invalid body (empty meaning, wrong `lang` format, note too long) |

Why one endpoint per edit: [decisions](../decisions.md#one-endpoint-per-customisation).

## `POST /library/entries/own`

Creates a word of the user's own, one the dictionary doesn't have
([`CreateOwnEntry`](../application/use-cases.md#createownentryentries-collectionsexecuteuser_id-spellings-readings-meaning-lang-collection_ids)):

```json
{ "spellings": ["三匹"], "readings": ["さんびき"], "meaning": "three animals", "lang": "eng", "collection_ids": [3] }
```

`readings` (1–10, kana only), `spellings` (0–10, optional), `meaning` (1–500) in `lang`
(ISO 639-2), `collection_ids` (optional). `201` with the entry: `source_entry_id` is
`null` and every part has `origin: "added"`. `404` for a collection that isn't the
user's (nothing is created), `422` for an invalid body.

## `POST /library/entries`

Imports a dictionary entry into the current user's library
([`ImportEntry`](../application/use-cases.md#importentrydictionary-entries-collectionsexecuteuser_id-source_entry_id-collection_ids)).

Request body (`collection_ids` is optional):

```json
{ "entry_id": 1358280, "collection_ids": [3, 7] }
```

`collection_ids` (at most 50) are entry collections to put the entry in, in the same
transaction: if any of them isn't the user's, the request fails with `404` and nothing
is imported. They're added even when the entry was already in the library (`200`), so
"import into a collection" is a single, retry-safe request.

| Status | When | Body |
|---|---|---|
| `201` | Imported now | `PracticeEntryResponse` |
| `200` | Already in the library | the existing `PracticeEntryResponse` |
| `401` | See [authentication](authentication.md#errors) | `{"detail": ...}` |
| `404` | Not in the dictionary, or a collection isn't the user's | `{"detail": ...}` |
| `422` | Invalid body (e.g. more than 50 `collection_ids`) | validation errors |

`PracticeEntryResponse`: `id`, `source_entry_id` (`null` for a word of the user's own), `kanji_readings`, `readings`,
`senses` (with `glosses` and `examples`), `jlpt`, `is_common`, `is_active`,
`created_at`, `updated_at`. Nested items carry their `id`, `enabled` and, where
applicable, `origin`. `user_id` isn't exposed.

## `POST /library/kanji`

Imports a dictionary kanji
([`ImportKanji`](../application/use-cases.md#importkanjidictionary-kanji-collectionsexecuteuser_id-literal-collection_ids)).

Request body (`literal` must be exactly one character; `collection_ids`, kanji
collections, is optional and works as above):

```json
{ "literal": "食", "collection_ids": [2] }
```

Same status codes as above. `PracticeKanjiResponse`: `id`, `literal`, `grade`,
`stroke_count`, `freq`, `jlpt`, `on_readings`, `kun_readings`, `nanori`, `meanings`,
`is_active`, `created_at`, `updated_at`.

## `GET /dictionary/search`

Public dictionary search: no token needed
([`SearchDictionary`](../application/use-cases.md#searchdictionarydictionaryexecutequery-lang-limit-offset)).
It runs the same `Dictionary.search` as `shodoukan-api`'s `GET /search` through the
[dictionary gateway](../infrastructure/dictionary-gateway.md), so query detection
(kanji, kana, romaji, meaning) and ranking are identical. The practice app doesn't
depend on `shodoukan-api` being up. Why it's duplicated:
[decisions](../decisions.md#the-practice-app-has-its-own-dictionary-search).

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `q` | string, min 1 | required | Kanji, kana, Hepburn romaji or a meaning |
| `lang` | string | `en` | ISO 639-1 language meanings are matched in; results keep every language |
| `limit` | int, 1–100 | `20` | Entries per page |
| `offset` | int, ≥ 0 | `0` | Entries to skip |

| Status | When | Body |
|---|---|---|
| `200` | Always | `DictionarySearchResponse` |
| `422` | Missing or empty `q`, or out-of-range `limit` / `offset` | validation errors |

`DictionarySearchResponse` has the same shape as `shodoukan-api`'s response, so
frontend components can render either. It's this API's own model, so the two apps
can evolve separately:

```json
{
  "entries": {
    "items": [{ "id": 1358280, "kanji_readings": [...], "readings": [...],
                "senses": [...], "jlpt": 5, "is_common": true }],
    "total": 2, "limit": 20, "offset": 0
  },
  "kanji": [{ "literal": "食", "on_readings": ["ショク", "ジキ"], "meanings": [...], ... }]
}
```

Entry `id` is what `POST /library/entries` takes as `entry_id`, and kanji `literal`
is what `POST /library/kanji` takes. Compared to `shodoukan-api`, the practice API
omits priority tags, nested row ids, example provenance and debug scores, and cross
references use `sense_index`.

## Dictionary details

Public, like the search. They feed the entry and kanji detail pages and return the same
models as `GET /dictionary/search`
([`GetDictionaryEntry`, `GetDictionaryKanji`, `GetDictionaryKanjiStrokes`, `ListEntriesForKanji`, `ListKanjiForEntry`](../application/use-cases.md#queries-queriesdictionary_queriespy)).

| Method | Route | Response |
|---|---|---|
| `GET` | `/dictionary/entries/{entry_id}` | `DictionaryEntryResponse` |
| `GET` | `/dictionary/entries/{entry_id}/kanji` | `list[DictionaryKanjiResponse]`: the kanji in its spellings, empty for kana-only words |
| `GET` | `/dictionary/kanji/{literal}` | `DictionaryKanjiResponse` |
| `GET` | `/dictionary/kanji/{literal}/entries?limit&offset` | `DictionaryEntryPageResponse` (`items`, `total`, `limit`, `offset`): the words written with the kanji, ranked |
| `GET` | `/dictionary/kanji/{literal}/strokes` | `DictionaryKanjiStrokesResponse` (`literal`, `strokes`: `{path, label}` in writing order, KanjiVG's 109 × 109 space): same shape as shodoukan-api's [`/kanji/{literal}/strokes`](../../../technical/api.md#get-kanjiliteralstrokes); sent with `Cache-Control: public, max-age=86400` |

`404` when the entry or kanji isn't in the dictionary (for `/strokes`, when the
character has no KanjiVG drawing; it doesn't need to be a dictionary kanji), `422` for a `literal` that isn't
one character or an out-of-range `limit` (1–100, default `20`) / `offset` (≥ 0).

## `GET /library/imported`

Which of a set of dictionary items the current user has already imported
([`GetImportStatus`](../application/use-cases.md#getimportstatusentries-kanjiexecuteuser_id-source_entry_ids-literals)).
It's meant for the dictionary page: the page searches with
[`GET /dictionary/search`](#get-dictionarysearch) (public), then asks this in parallel
with the ids of the results, to enable or disable each Import button. Why two requests:
[decisions](../decisions.md#import-status-is-a-separate-request-from-dictionary-search).

Query parameters, each repeated, up to 100 of each (one search page):

```
GET /library/imported?entry_ids=1358280&entry_ids=2847337&literals=食&literals=噇
```

| Parameter | Type | Notes |
|---|---|---|
| `entry_ids` | int, repeated | Dictionary entry ids (`Entry.id` from the search) |
| `literals` | one character, repeated | Kanji from the search |

| Status | When | Body |
|---|---|---|
| `200` | Always, for a valid token | `ImportStatusResponse` |
| `401` | Missing or invalid token | `{"detail": ...}` |
| `422` | More than 100 of a kind, or a `literals` value that isn't one character | validation errors |

`ImportStatusResponse` lists **only the imported items**, with their practice ids.
Anything asked about and missing from the response isn't imported:

```json
{
  "entries": [{ "source_entry_id": 1358280, "id": 1 }],
  "kanji": [{ "literal": "食", "id": 3 }]
}
```

Deactivated items still count as imported.

## `GET /health`

Liveness check for Docker healthchecks and the deploy smoke test: `200
{"status": "ok"}`, with no token, database or identity provider involved.

## `GET /users/me`

The current user's practice profile. On the first request of a new identity, the user
is created ([`EnsureUser`](../application/use-cases.md#ensureuserusersexecuteuser_id-username)),
so the frontend can call this right after sign-in.

| Status | When | Body |
|---|---|---|
| `200` | Always, for a valid token | `UserResponse`: `id` (the identity provider's user id, a UUID: equal to the token's `sub`), `username`, `created_at` |
| `401` | Missing or invalid token | `{"detail": ...}` |


## Collections

Two routers with the same shape: `/collections/entries` for entry collections and
`/collections/kanji` for kanji collections (they never mix). Code:
`routes/collection_routes.py`, `schemas/collection_schemas.py`. All need a token.
Lookups are scoped to the user, so another user's collection or item is a `404`, the
same as a missing one.

| Method | Route | Use case | Success |
|---|---|---|---|
| `GET` | `/collections/entries` | `ListEntryCollections` | `200` `list[CollectionResponse]`, by name |
| `POST` | `/collections/entries` | `CreateEntryCollection` | `201` `CollectionResponse` |
| `GET` | `/collections/entries/{collection_id}` | `GetEntryCollection` | `200` `CollectionResponse` |
| `PUT` | `/collections/entries/{collection_id}` | `UpdateEntryCollection` | `200` `CollectionResponse` |
| `DELETE` | `/collections/entries/{collection_id}` | `DeleteEntryCollection` | `204` (the entries stay in the library) |
| `GET` | `/collections/entries/{collection_id}/items` | `SearchEntries` (`in_collection`) | `200` `PracticeEntryPageResponse` (`items`, `total`, `limit`, `offset`) |
| `PUT` | `/collections/entries/{collection_id}/items/{entry_id}` | `AddEntryToCollection` | `204`, idempotent |
| `DELETE` | `/collections/entries/{collection_id}/items/{entry_id}` | `RemoveEntryFromCollection` | `204`, idempotent |

The kanji routes are the same under `/collections/kanji`, with `{kanji_id}` and
`PracticeKanjiPageResponse`. Item ids are **practice** ids (the `id` returned by the
import), not dictionary ids.

`POST` and `PUT` take a `CollectionRequest`:

```json
{ "name": "verbs", "description": "Godan and ichidan" }
```

`name` is stripped and must be 1–100 characters; `description` is optional. `PUT`
replaces both fields, so an omitted `description` clears it. `CollectionResponse`:
`id`, `name`, `description`, `created_at`, `updated_at`.

`GET .../items` takes `limit` (1–100, default `20`), `offset` (≥ 0, default `0`) and
`active` (`true` only active items, `false` only deactivated ones; all if omitted, as
in the library) and returns a page of the items in the order they were added, with
their `total`, the same shape as `GET /library/entries`. `q` and `meaning_lang` search
within the collection exactly as in [the library](#get-libraryentries-and-get-librarykanji).

| Status | When |
|---|---|
| `401` | Missing or invalid token |
| `404` | No such collection, or no such item in the user's library |
| `409` | The user already has a collection of that kind with that name (`POST`, `PUT`) |
| `422` | Invalid body, name, `limit` or `offset` |

## Exercises

Saved exercise definitions; design in [exercises](../exercises.md). Code:
`routes/exercise_routes.py`, `schemas/exercise_schemas.py`. All need a token; another
user's exercise or collection is a `404`.

| Method | Route | Use case | Success |
|---|---|---|---|
| `GET` | `/exercises` | `ListExercises` | `200` `list[ExerciseResponse]`, by name |
| `POST` | `/exercises` | `CreateExercise` | `201` `ExerciseResponse` |
| `GET` | `/exercises/{exercise_id}` | `GetExercise` | `200` `ExerciseResponse` |
| `PUT` | `/exercises/{exercise_id}` | `UpdateExercise` | `200` `ExerciseResponse` |
| `DELETE` | `/exercises/{exercise_id}` | `DeleteExercise` | `204` (the collections stay) |

`POST` takes a `NewExerciseRequest`; `PUT` an `ExerciseRequest`, the same without
`item_kind` (it can't change; a sent one is ignored), and replaces every field:

```json
{
  "item_kind": "kanji",
  "name": "N5 kanji",
  "description": null,
  "collection_ids": [3],
  "settings": {
    "type": "card.choice",
    "directions": [
      { "prompt": ["literal"], "answer": "kunyomi" },
      { "prompt": ["kunyomi"], "answer": "literal" }
    ],
    "back_fields": ["meaning"],
    "option_count": 4
  }
}
```

- `name`: stripped, 1–100 characters. `collection_ids`: at least one, collections of
  the exercise's kind.
- `settings` is the domain's settings model as JSON, keyed by `type`: `card.choice`,
  or `card.handwriting` (every direction's `answer` is something to write: `literal`
  for kanji, `writing` or `reading` for entries; no options). Omitted settings take their defaults (`back_fields` `[]`,
  `option_count` `4`, `distractor_source` `"collection"`). A `question_count` sent by
  older clients is ignored.
- Fields: `writing`, `reading`, `meaning` for `entries`; `literal`, `onyomi`,
  `kunyomi`, `meaning` for `kanji`.

`ExerciseResponse`: `id`, `name`, `description`, `item_kind`, `collection_ids` (empty if
its collections were deleted: it can't run until it gets one), `settings` with every
default filled in, `created_at`, `updated_at`.

| Status | When |
|---|---|
| `401` | Missing or invalid token |
| `404` | No such exercise, or a collection that isn't one of the user's of that kind |
| `422` | Invalid body: name, no collection, unknown `type`, no direction, a direction asking for a field it shows, a repeated direction or back field, `option_count` outside 2–8, or a field of the other item kind |

## Exercise sessions

Studying an exercise; design in [exercises](../exercises.md#sessions-built). Code:
`routes/exercise_session_routes.py`, `schemas/exercise_session_schemas.py`. All need a
token; another user's exercise or session is a `404`.

| Method | Route | Use case | Success |
|---|---|---|---|
| `POST` | `/exercises/{exercise_id}/sessions` | `StartExerciseSession` | `201` `SessionResponse` with its first active question |
| `GET` | `/exercise-sessions` | `ListExerciseSessions` | `200` `SessionSummaryPageResponse` |
| `GET` | `/exercise-sessions/{session_id}` | `GetExerciseSession` | `200` `SessionResponse` |
| `POST` | `/exercise-sessions/{session_id}/answer` | `AnswerExerciseQuestion` | `200` `AnswerResponse` |
| `POST` | `/exercise-sessions/{session_id}/finish` | `FinishExerciseSession` | `200` `SessionResponse`, idempotent |

Starting takes `{"meaning_lang": "en"}`: the language of meanings as the items store
it (2–3 lower-case letters; `eng` for entries, `en` for kanji, like `meaning_lang` on
the library lists); it finishes the user's open session, of any exercise (one at a
time).
Answering takes
`{"question_id": 12, "answer": {"type": "option", "option": 2}, "response_ms": 1500}`:
`question_id` must be the active question's, and `response_ms` is optional (0 to
2147483647, what its 32-bit column holds). `{"type": "skip"}` as the answer skips the
question: it's graded as a miss and returned with its solution, like any answer. A
handwriting card is answered with the drawing,
`{"type": "strokes", "strokes": [[[x, y], ...], ...]}`: the strokes in the order
drawn, in KanjiVG's 109-unit square, with a margin of 6 allowed around it (up to 40
strokes of up to 300 points). A word is answered with a drawing per character,
`{"type": "cells", "cells": [[[[x, y], ...], ...], ...]}`, in the same space, as many
cells as the question's `cell_count` (a cell may be empty, not all). An answer of
another type, the wrong number of cells, or points off the canvas, is a `422`.
Starting a handwriting exercise whose collections have fewer than 2 kanji (or words)
with every stroke order is a `422` too.

Listing is the history: the user's sessions, newest first, **without their
questions**. Query: `exercise_id` (one exercise's sessions; an unknown or deleted one
isn't a `404`, since sessions outlive their exercise), `status` (`open` or
`finished`; idle sessions are finished), `limit` (1–100, default 20), `offset`
(default 0). `status=open&limit=1` is the session to resume. A
`SessionSummaryPageResponse` is `items`, `total` (across every page), `limit` and
`offset`; each `SessionSummaryResponse` has `id`, `exercise_id` (null if deleted),
`exercise_name`, `item_kind`, `started_at`, `last_activity_at`, `finished_at` (the
effective one, as in `SessionResponse`), `answered` and `score`.

`SessionResponse`: `id`, `exercise_id` (null if the exercise was deleted),
`exercise_name`, `item_kind`, `meaning_lang`, `started_at`, `last_activity_at`,
`finished_at` (also set, to the last activity, for a session idle over 30 minutes),
`answered`, `score`, `current` (the active question; null once finished) and
`history` (the answered questions, in order). Each question is a union keyed by
`type`, so the client picks the player by type. Every question has `id`, `position`,
`prompt_fields`, `answer_field`, `prompt` (`[{field, values}]`), `answered`, and the
solution fields `item_id`, `back`, `answer`, `is_correct`, `answered_at` and
`response_ms`.

- `"card.choice"` adds `options` (`[{text, item_id}]`) and `correct_option`.
- `"card.handwriting"` adds `references` (`[{literal, strokes: [{path, label}]}]`,
  the KanjiVG strokes of every kanji it accepts) and `grade` (`{score, verdict,
  matched, strokes: [{drawn, reference, status}]}`; null when skipped).
- `"card.handwriting_word"` adds `cell_count` (always shown: the cells to write in),
  `words` (`[{text, characters: [{literal, strokes}]}]`, every word it accepts) and
  `grade` (`{score, verdict, matched, cells: [<a kanji's grade>]}`; null when
  skipped). A cell's grade may have `looks_like`, the character it was taken for
  (ろ for る).

**The active question hides its solution:** the solution fields are null, and so are
`correct_option` and each option's `item_id`, or `references` (`words`) and `grade`. `AnswerResponse`: the graded
question (`answered`) with its solution, the `next` active question (null if the pool
can't make another, or if the exercise was deleted, which finishes the session),
`answered_count`, `score` and `finished_at`.

| Status | When |
|---|---|
| `401` | Missing or invalid token |
| `404` | No such exercise or session for this user |
| `409` | Starting: another session was started at the same moment. Answering: the session is finished, or idle for over 30 minutes; `question_id` isn't the active question (answered already, e.g. a double click) |
| `422` | Invalid body or `meaning_lang`; an option the question doesn't have; or the exercise's collections have too few usable items (`ExercisePoolTooSmallError`, with the reason in `detail`). Listing: `status`, `limit` or `offset` out of range |

## Exercise statistics

How the user does, computed from the answered questions on every request
([design](../exercises.md#history-and-statistics-built-42)). Code:
`routes/exercise_statistics_routes.py`, `schemas/exercise_statistics_schemas.py`.
Read-only; both need a token.

| Method | Route | Use case | Success |
|---|---|---|---|
| `GET` | `/exercises/{exercise_id}/statistics` | `GetExerciseStatistics` | `200` `ExerciseStatisticsResponse` |
| `GET` | `/statistics?days=30&tz=UTC` | `GetPracticeStatistics` | `200` `PracticeStatisticsResponse` |

`accuracy` is `correct / answered` (0 to 1), null when nothing was answered, so
clients needn't divide. `TotalsResponse`: `sessions` (with at least one answer),
`answered`, `correct`, `accuracy`, `mean_response_ms` (null if no answer was timed).
`MissedItemResponse`: `item_id` (the library id), `label` (a word's usual form, or the
kanji), `reading` (a word's reading when `label` is a spelling, else null),
`answered`, `wrong`; most misses first, at most 10, items no longer in the library
left out.

- **Per exercise:** `exercise_id`, `item_kind`, `totals`, `directions` (most answered
  first; each `prompt_fields` sorted, `answer_field`, `answered`, `correct`,
  `accuracy`; the same fields in another order are one direction) and `most_missed`
  (items of the exercise's kind).
- **Overall:** `days` (1–365, default 30) and `tz` (an IANA time zone, default `UTC`).
  `totals`, `activity` (one `{day, answered, correct}` per day of the window in `tz`,
  oldest first, today last, days without answers included), `exercises` (per exercise
  with answers, most recently answered first, under its current name; deleted ones
  left out: `exercise_id`, `exercise_name`, `item_kind`, `sessions`, `answered`,
  `correct`, `accuracy`, `last_answered_at`), `most_missed_entries` and
  `most_missed_kanji`.

| Status | When |
|---|---|
| `401` | Missing or invalid token |
| `404` | Per exercise: no such exercise for this user |
| `422` | Overall: unknown time zone, or `days` out of range |

## Conventions

- **Schemas** (`schemas/<subject>_schemas.py`) are separate from domain entities, so the
  API contract doesn't change when the domain does. Responses are built with
  `model_validate(entity)` (`from_attributes`).
- **Dates** are ISO 8601 UTC with `Z`; see [dates](../cross-cutting/dates-and-time-zones.md).
- **CORS:** the frontend calls the API from the browser with an `Authorization`
  header, so `app.py` enables CORS for `CORS_ORIGINS` (methods `GET`/`POST`/`PUT`/`DELETE`, headers
  `Authorization`/`Content-Type`). It's the same variable `shodoukan-api` uses; see
  [configuration](../cross-cutting/configuration.md).
- **Domain errors → HTTP** (exception handlers in `app.py`):
  `DictionaryItemNotFoundError` and `EntityNotFoundError` → `404`,
  `CollectionNameTakenError`, `OriginalDataError`, `QuestionNotActiveError` and
  `SessionFinishedError` → `409`,
  `ExercisePoolTooSmallError` and `InvalidAnswerError` → `422` (message in `detail`). Authentication errors are raised as `HTTPException`s in `deps.py`.
- **Entity validation → `422`.** A Pydantic `ValidationError` raised inside a use case
  (an entity built or changed against its rules, e.g. exercise settings with fields of
  the other item kind) is answered `422` with `detail` shaped like FastAPI's request
  validation errors (without `input` or `url`). Response serialisation errors are a
  different exception and stay `500`.

## Transactions

`deps.get_session()` opens one `Session` per request, shared by the repositories
built for it. Routes **commit explicitly** after the use case succeeds and before
responding, so a commit failure can't follow a success response. Anything not
committed is rolled back when the session closes.

## Wiring (`deps.py`)

| Dependency | Provides |
|---|---|
| `get_session` | the request's `Session` |
| `get_token_verifier` | `TokenVerifier.from_env()`, cached per process |
| `_oauth2` | the OAuth2 (authorization code) security scheme: extracts the bearer token and documents the Keycloak login for Swagger |
| `get_current_user` | the `User` behind the bearer token, created on first use (`EnsureUser`) |
| `get_dictionary_gateway` | `ShodoukanDictionaryGateway` over a cached `Dictionary()` |
| `get_import_entry` / `get_import_kanji` / `get_import_status` / `get_list_library_entries` / `get_list_library_kanji` | use cases with SQLAlchemy repositories on the request's session |
| `get_<use case>` for collections (`get_create_entry_collection`, `get_add_kanji_to_collection`, ...) | one factory per collection use case, with the collection and item repositories on the request's session |
| `get_list_exercises`, `get_get_exercise`, `get_create_exercise`, `get_update_exercise`, `get_delete_exercise` | exercise use cases, with the exercise and both collection repositories on the request's session |
| `get_start_exercise_session`, `get_answer_exercise_question`, `get_finish_exercise_session`, `get_get_exercise_session` | session use cases: exercises, sessions, both collection and both item repositories on the request's session (a fresh `random.Random` per start) |
| `get_list_exercise_sessions` | the history, over the session repository |
| `get_get_exercise_statistics`, `get_get_practice_statistics` | statistics use cases: the statistics repository and both item repositories (plus the exercise repository per exercise) on the request's session |
| `get_get_library_entry`, `get_set_entry_notes`, `get_add_kanji_meaning`, ... | one factory per library item use case, on the request's session |
| `get_search_dictionary`, `get_get_dictionary_entry`, `get_get_dictionary_kanji`, `get_get_dictionary_kanji_strokes`, `get_list_entries_for_kanji`, `get_list_kanji_for_entry` | dictionary use cases over the gateway (no session, no user) |

Tests replace `get_session`, `get_dictionary_gateway` and `get_token_verifier` with
`app.dependency_overrides`.
