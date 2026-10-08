# Design Decisions

[← Technical documentation](README.md)

A short log of the non-obvious choices in the practice app, newest last. Each entry
says what was decided and why, so it isn't re-litigated or accidentally undone. If a
decision is reversed, add a new entry instead of editing the old one.

## Collections double as tags

A tag and a collection are the same data: a named group plus an m:n link to items.
There is one concept, `Collection`. Tagging an item is adding it to a collection.

## Collections don't hold their members

`Collection` is metadata only. Membership lives in link tables and goes through the
repository (`add_item`, `item_ids`; reading a collection's items is the item
repositories' `find` with `InCollection`), so listing cards paginates
and sorts in SQL, tagging is a single INSERT, and nothing loads a whole collection.

## Entry and kanji collections are subclasses

Entries and kanji are never studied together. A `kind` field was replaced by
`EntryCollection` / `KanjiCollection`: the type says what a collection holds, each
has its own tables with real foreign keys, and code that only needs the grouping uses
the `Collection` base.

## Ports take typed entities, not ids

Entry and kanji collection ids come from different tables and can collide. Ports take
`KanjiCollection` rather than an `int`, and mypy (nominal typing) rejects mixing them.
The application loads the collection anyway, to answer "not found" or "not yours".

## Protocols for repository ports

`typing.Protocol` by default: implementations needn't import the domain, and mypy
checks conformance. Implementations still inherit their Protocol explicitly to be
checked at the definition. An `ABC` is fine where runtime enforcement, shared helpers
or `isinstance` checks are needed.

## PostgreSQL, normalized snapshot

PostgreSQL in every real environment, SQLite in unit tests. The nested snapshot is
normalized (one table per level) so enabling, disabling or adding one gloss or reading
is a single-row write with a stable id.

## Repositories never commit

The caller (use case / request) owns the transaction. Repositories flush only, so
several of them share one unit of work.

## Naive UTC in the database, aware UTC in the backend

The database stores naive UTC, the backend works with aware UTC (`UtcDateTime`), and
the API will send ISO 8601 with offset, so clients convert to local time.

## The domain decides "now"; no database defaults for timestamps

Timestamps come from `utc_now()` in the domain; aggregates bump `updated_at` with
`touch()` from their mutation methods. Database defaults only pay off when something
writes to the database without going through the app. Here they would hide dates from
the entity until after the insert, fight the domain's `updated_at`, make time hard to
control in tests, and need dialect-specific SQL (`timezone('utc', now())` on
PostgreSQL, which SQLite lacks). Performance and scale are the same either way.
Revisit if a non-app writer appears, and then add a `server_default` only as a safety
net.

## The dictionary is used in-process behind a port

`shodoukan` already is the shared library: `shodoukan-api` is a thin FastAPI layer over
`shodoukan.Dictionary`. The practice app uses it the same way, in-process, behind a
`DictionaryGateway` port, and wires its own cached instance (nothing is shared with
the API beyond the library). The practice app only needs the dictionary at import
time, since imported items are snapshots. Considered and rejected for now:

- **HTTP calls to `shodoukan-api`:** one owner of the data, but it adds latency,
  failure handling and an API contract to keep stable.
- **Merging both apps:** one deployable, but read-only search and per-user writes
  would share their scaling and deploy cycle.
- **A new common package:** `shodoukan` already is that package.

The port makes an HTTP adapter a drop-in replacement if the services need to be split.
The gateway returns domain entities, and an anti-corruption mapper keeps the
dictionary's models out of the domain.

## Romaji goes through a `KanaGateway` port

Searching the library by reading needs romaji converted to kana and kana in both
scripts. `shodoukan` already has those tools (the dictionary search uses them), so the
practice app reuses them instead of keeping a second romaji table. Like the dictionary,
they're reached through a port (`KanaGateway`, implemented by `ShodoukanKanaGateway`
next to the dictionary gateway): the domain and use cases don't import `shodoukan`, and
the converter can be faked in tests.

## Library search is one module over the item repositories

The library, a collection and the "add to collection" picker all search the same items
with a different scope. The search is one module at the logical level:
`domain/searches/` holds what a search is (`LibrarySearch`, `MatchTier`, scopes) and
the search use cases share the normalization, collection ownership and paging. The
item repositories run it (`find` / `count` with a scope), replacing their list methods.

- **A collection's items are read from the item repositories**, not the collection
  repositories. The result is `PracticeEntry` / `PracticeKanji` aggregates, which those
  repositories already load and map; a collection is metadata plus links (see "Collections
  don't hold their members"). Reading them from the collection side would make that
  repository know about readings and glosses and duplicate the hydration.
- **Repositories, not separate finders.** The backend conventions put listing,
  ordering and paging in repositories. A finder would return the same aggregates from
  the same tables with the same mappers: two ports per aggregate for no real
  difference. Worth revisiting if lists start returning a lighter read model instead
  of aggregates, or the search moves to another engine (an external index, a replica):
  use cases depend only on the port, so the change stays in infrastructure and wiring.
- **No specification pattern.** Match tiers are named constants and the SQL applies
  them; with one engine, a rule interpreter adds nothing.

## Library search is SQL over the normalized snapshot

Every reading, gloss and meaning already has its own row, so searching is SQL with
`LIKE` over those tables, scoped to the user. Considered:

- **PostgreSQL full-text search:** its stemming and word splitting are made for
  European languages and don't help with Japanese.
- **An external engine (Meilisearch, Elasticsearch):** a second store to keep in sync
  for a per-user library of hundreds to a few thousand items.
- **A trigram index (`pg_trgm`):** the next step if `LIKE '%…%'` gets slow; it speeds
  up the same queries without changing them or the API.

## Keycloak, with the API as a resource server

Users sign in with Keycloak (OIDC). The API only verifies access tokens (RS256 against
the realm's JWKS, plus `exp`, `iss` and optionally `aud`) and identifies the user by
`sub`, stored as `users.subject`. No passwords or login code live in this repo.

## Unregistered users are rejected

A valid token whose `sub` has no practice user gets `403`. Users aren't created on
first sight; a registration use case will create them. This keeps account creation
an explicit step.

## Imports are idempotent and keep every language

Importing an item the user already has returns that copy (`200`) instead of failing,
so double clicks and retries are harmless. A concurrent duplicate is handled with a
savepoint (`add_if_absent`). The snapshot keeps every language the dictionary has: the
UI filters by language, and switching language never needs a re-import.

## One session per request; routes commit

The request's `Session` is shared by every repository it uses. Use cases don't commit;
the route commits after the use case succeeds and before responding, so the client
never gets a success response for a transaction that then fails to commit.

## External identity provider instead of our own user management

Sign-up, sign-in, password storage and reset, sessions, brute-force protection, MFA and
social login stay with an OpenID Connect provider (Keycloak locally). Building them in
the practice API would put the most security-sensitive code of the system in our hands
for little gain. The API is written against the standard (signature, `iss`, `aud`,
`exp`), so the provider can be self-hosted Keycloak or a managed service in
production, changing configuration only.

## Users are created on their first request

This **replaces** "Unregistered users are rejected". The identity provider already
decides who may sign up, so any identity it vouches for gets a practice user on its
first request (`EnsureUser`, `GET /users/me`). There's no 403 any more. `username` is
the provider's display name, so it isn't unique and isn't updated after creation.

## Keycloak has its own database container

Keycloak stores its realm, users and sessions in a dedicated `keycloak-db` Postgres,
not in `practice-db`. It starts from an empty image and Keycloak creates its own
tables, so there are no init scripts or extra users to manage. Its environment lives in
its own `.env.keycloak`, and the identity provider can run, be upgraded or move
independently of the practice API, as it would in production.

## Users are keyed by the identity provider's UUID

`users.id` **is** the provider's user id (the token's `sub`, a UUID), and every
`user_id` foreign key is a UUID. This replaces the integer id plus `subject` column: a
strict 1:1 with provider users, with no second id to keep in sync, and the same id in
the API, the database and Keycloak. The cost is that the provider must issue UUID
`sub`s (Keycloak, Cognito and Supabase do; Auth0, Google and Okta don't), and tokens
with any other `sub` get `401`. Switching to such a provider would need an id-mapping
column again.

## Migrations squashed before the first deploy

The integer-to-UUID change was folded into a single regenerated initial migration
instead of a conversion migration, although the original initial migration had
already been pushed to the feature branch. No environment had ever applied it (the
practice database has never been deployed and the branch wasn't merged), so there was
no data to convert. This is the only exception to "never edit a pushed migration", and
it ends with the first deployment.

## Import status is a separate request from dictionary search

The dictionary page searches with `shodoukan-api`'s public `GET /search` and, in
parallel, asks the practice API `GET /library/imported` with the ids of the results.
Search is the same for everyone: public, cacheable, and no sign-in needed to browse.
Import status is per user: it needs a token and the practice database. Merging them
would make every search require sign-in, defeat shared caching, make search depend on
PostgreSQL, and duplicate `shodoukan-api`'s search in the practice API. The cost is a
second, short request. Searching the user's own imported data (the collection page)
is a separate, future use case.

## The practice app has its own dictionary search

The dictionary and the practice app are **standalone applications** that may evolve
separately. So the practice API exposes `GET /dictionary/search` itself instead of
relying on `shodoukan-api` being up, and the dictionary page searches there. This
partly supersedes "Import status is a separate request from dictionary search": status
is still a separate per-user request, but the search now comes from the practice API.
Nothing is reimplemented: both apps call the `shodoukan` library's `Dictionary.search`,
so query detection and ranking stay identical, and search changes belong in the
library. The response has `shodoukan-api`'s shape (so UI components can serve both)
but is the practice API's own read model (`Dictionary*`), translated in the
anti-corruption mapper so the two APIs' contracts can diverge.

## Collection name clashes come from the unique constraint

A user can't have two entry (or two kanji) collections with the same name. The
repository doesn't look the name up before writing: it writes in a savepoint and turns
the `UNIQUE(user_id, name)` violation into `CollectionNameTakenError`. A pre-check
alone would let two concurrent requests both pass it, and the loser would get a `500`
instead of a `409`.

## Collection updates replace name and description

`PUT /collections/{kind}/{id}` takes the whole `CollectionRequest` and replaces both
fields, instead of a `PATCH` with optional fields. With only two editable fields the
client always has both, and the use case stays typed (`name: str`,
`description: str | None`) without a sentinel to tell "not sent" from "cleared". The
cost: an omitted `description` clears it. If collections gain more fields, revisit
with a `PATCH`.

## Dictionary data in the library is only ever disabled

The library copy is the user's, but its dictionary data (readings, spellings, examples
and imported meanings) is never edited or deleted: the user disables what they don't
want. Only meanings they added themselves can be edited and removed. This keeps the
original always recoverable (re-enable it), keeps an "imported" item meaning the same
thing as the dictionary, and lets a future re-sync with the dictionary tell the
user's additions apart. Readings can't be added for now: it's rarely needed and would
need an `origin` column on the reading tables.

## One endpoint per customisation

Each edit of a library item is its own small request (`PUT .../notes`,
`PUT .../{part}/{id}/enabled`, `POST .../glosses`, ...) instead of a `PATCH` of the whole
document. Each maps to one domain method, so the rules (only own meanings change) are
enforced where they live, the UI saves each toggle or note as the user makes it, and two
tabs editing different parts don't overwrite each other. Every edit returns the whole
item so the client doesn't have to merge.

## The practice frontend is a Nuxt 4 SPA with Nuxt UI

`shodoukan-practice-web` is built with Nuxt UI 4, which needs Nuxt 4, while the
dictionary web stays on Nuxt 3. Nuxt UI gives the dashboard layout (collapsible
sidebar, panels), forms, overlays and toasts ready-made and accessible, with an official
Claude Code skill for its conventions. The dictionary cards come from `shodoukan-ui`
(built with Tailwind 3 into its own CSS), so the two Tailwind versions don't meet.

It renders only in the browser (`ssr: false`): every screen needs the signed-in user's
token, which lives in the browser, so the server would render nothing useful and would
complicate the sign-in flow. Sign-in uses `oidc-client-ts`, written against the OpenID
Connect standard like the API, so the identity provider can change by configuration.

The item detail is a page shared by the library and collections, not a modal, so it has
its own URL and the back button works.

## Importing into collections is one request

The dictionary lets the user pick a collection for an item that isn't imported yet.
`POST /library/entries` and `/library/kanji` take optional `collection_ids` instead of
the frontend chaining the import and `PUT /collections/.../items/...`: two requests can
fail halfway and leave the item imported but outside the collection the user chose.
One request runs in one transaction, checks the collections before importing (an
unknown one imports nothing), and stays idempotent, so a retry is safe. Every client
gets that guarantee without repeating the logic. Adding an already-imported item to a
collection keeps using the collection endpoints.

## One collection picker, two modes

The dictionary and the library each had their own "add to a collection" control (a
popover with checkboxes, and a searchable select), and they had already drifted: one
could create collections, the other could search. They're now one presentational
component, `CollectionPicker` (a `USelectMenu`: search, `multiple` and `create-item`
come with it), and the data lives in `useItemCollections`. Vue has no component
inheritance, so the dictionary's version is a wrapper (`CollectionMenuButton`) that adds
what only the dictionary needs: importing the item before adding it.

The two modes differ on purpose. A dictionary card has nowhere else to show which
collections an item is in, so its menu ticks them and lets the user untick. The library
page already lists them as removable badges, so its menu shows only the others.

Collections are created by typing a new name in the search, not with the form modal:
it's one gesture and the item goes straight in. The description is left for the
collections page.

## Exercises: the server builds and grades the questions

A session's questions (item, direction, options) are generated by the practice API,
and answers are graded there. The client could build them from a collection's items,
but then statistics would be whatever the client reports, the whole collection would
have to be paged into the browser, and library-wide distractors (planned) would need
the whole library. The cost is one request per answer. See
[exercises](exercises.md).

## Exercise sessions are the statistics

Each question of a session stores a snapshot of its prompt, options and back, plus the
answer and whether it was right. Reviewing a session and computing accuracy are
queries over those rows. No separate statistics store is kept in sync, and the
snapshot keeps old sessions readable after items change or are removed. (What the
snapshot holds besides the prompt and back depends on the question type: see
[questions are a union too](#questions-are-a-union-too-with-what-each-type-adds-in-one-json-column).)

## Exercise settings are JSON behind a discriminated union

An exercise's `settings` (directions, back fields, options...) differ per exercise
type and are always read and written whole, so they're one JSON column validated by
the domain's Pydantic union (keyed by `type`). New exercise types add a union member,
not tables or columns. The library snapshot is normalized for the opposite reason:
single parts are toggled and searched. The queryable data of answers (item, field,
right or wrong, time) gets real columns for statistics.

## Entry and kanji exercises are subclasses in one table

`EntryExercise` and `KanjiExercise` follow collections (the type says which fields and
which collections are valid), but share one `exercises` table with an `item_kind`
column, since their columns are the same and sessions need one id space to point at.
Their collections go in two link tables (`exercise_entry_collections`,
`exercise_kanji_collections`) so each has a real foreign key.

## An exercise holds its collection ids

Unlike a collection's members, an exercise's collections are part of its definition:
a handful of ids, always read with it and replaced whole on edit. So
`collection_ids` is a field of the entity, stored in the link tables by the
repository, instead of separate repository methods. A deleted collection drops out of
its exercises through the foreign key cascade.

## Distractors are never valid answers

A wrong option of a choice card is checked against every item that fits the prompt,
comparing normalized keys (katakana as hiragana, okurigana marks removed, glosses one
by one without "to " or parentheses). Shared on'yomi, homophones and synonyms are
common, and an option that is "wrong" but actually right would teach the wrong thing
and spoil statistics. A question with fewer options is preferred over an ambiguous
one. Details: [exercises](exercises.md#distractors-a-wrong-option-must-never-be-right).

## A word is asked by its usual form

A word's other spellings and readings are mostly variants (ヤマ for やま, がわ for かわ,
聴く for 聞く). Asking or offering one at random made odd forms the "right" answer,
so only the first enabled spelling and reading of a word are asked, offered and shown
on the card front; the back shows them all, and all are still compared for
ambiguity. The dictionary lists the usual form first, and disabling it in the library
picks the next. A kanji's readings are different things to learn, so any enabled one
can be asked.

## Session solutions are hidden until answered

Questions are sent when the session starts, so the client can show them without a
request per card. Their solution (the item, the right option, the back, the options'
items) is left out of the response until the question is answered: the right option
would otherwise be one look at the network tab away, and an option's item id would
give it away. Grading happens on the server either way.

## Sessions are open-ended, with one active question

This **replaces** sessions of a fixed number of questions built when they start
(`question_count` is gone). A session lasts as long as the user studies: it has one
active question, and answering it moves it to the history and asks the next one,
which is returned with the grade (one request per card). The next question is built
from the history, so nothing else has to be stored to avoid repeats, and items added
or deactivated mid-session count straight away. The active question is stored, not
kept in memory, so a reload shows the same card and the answer is graded against the
options really shown. Only that question is ever sent unanswered, still without its
solution (see "Session solutions are hidden until answered").

## The next item: a deck, plus missed items coming back

Each round deals every item once in random order, so nothing is left out and nothing
repeats too soon. An item answered wrong comes back after a few questions
(`REVIEW_GAP`), but reviews never come two in a row: in a run on real data where
most answers were wrong, misses alone took every turn and most items were never
asked. Spaced repetition across sessions is a later step that can reuse the history.

## Sessions close explicitly or when idle

The client finishes a session when the user leaves it, but browsers don't reliably
report a closed tab. So a session also ends when another one of the same exercise
starts, or after 30 minutes without activity, in both cases at its last activity, so
its duration isn't inflated. An idle session is reported as finished when read (no
write) and closed for good the next time it's used. The unanswered active question of
a finished session is dropped: it says nothing about what the user knows.

## An idle session isn't closed by an answer

This **replaces** "closed for good the next time it's used" in "Sessions close
explicitly or when idle". Answering an idle session closed it and then refused the
answer, but the refusal is an error, so the route never committed and the close was
rolled back. Rather than commit on an error path, an idle session is simply not
written there: `ask` and `answer` refuse it (`ended_at(now)`), and it's stored as
finished, at its last activity, when the user finishes it or starts the exercise
again. Abandoned sessions keep `finished_at` NULL either way, so "open" is defined by
`finished_at` and the idle timeout together.

## Answers to a session are serialized

A double click sent two answers to the same question; both read the session before
either stored it, so both succeeded, each asked a different next question, and one
answer could silently overwrite the other. Answering and finishing now lock the
session row (`SELECT ... FOR UPDATE`) for the transaction: the second request waits,
then finds the question answered and gets `409`. `UNIQUE(session_id, position)` on
the questions backs it up in the database, the same way collection names rely on
their unique constraint rather than a check: a second writer can't store a question
at a position that's taken.

## One open session per user

This **replaces** "one open session per exercise". A user studies one session at a
time, so starting any exercise closes their open session, of whatever exercise, at its
last activity. It also makes the locking cheap: there's at most one session per user
to lock.

Starting is serialized per user: it locks the user's row, then reads their open
sessions locked (`list_open`), closes them and inserts the new one. Without the locks,
a start racing an answer in another tab could save an old copy of the session and
delete the question just answered, and two starts could leave two open sessions. A
partial unique index (`user_id WHERE finished_at IS NULL`) backs the rule in the
database; its migration first closed the extra open sessions left by the per-exercise
rule. Answering and finishing lock only the session, never the user, so there's no
lock-order deadlock.

## Read models for history and statistics come from ports

This **extends** "Repositories, not separate finders" in "Library search is one
module over the item repositories", which said to revisit when lists return a lighter
read model. The session history and the statistics do: `SessionSummary` (a session
without its questions) and the statistics' `AnswerTotals`, `DirectionTotals`,
`ItemTotals`, `ExerciseTotals` and `AnswerMoment`. They're frozen Pydantic models
defined with their port in `domain/repositories/`, like the dictionary read models
with their gateway, and returned by repository methods: the history by
`ExerciseSessionRepository.list_summaries` / `count_summaries`, the statistics by a
new read-only `ExerciseStatisticsRepository`. It keeps the repository role and name
rather than a new "reader" or "finder" role: one kind of port for everything the
database answers, and use cases still depend only on the port.

## Statistics are SQL aggregates, computed on request

Following "Exercise sessions are the statistics", every figure (totals, accuracy per
direction, most missed items, per exercise) is a `GROUP BY` over the answered
`exercise_questions` joined to their session for the owner, run on every request.
Nothing is precomputed or cached, so there's nothing to keep in sync and no
migration was needed. The most missed items take their name from the **current**
library item (a word's usual form as asked, `entry_label`), not the snapshot, and
items that left the library aren't listed.

## One idle rule for sessions and their summaries

A session is open while `finished_at` is NULL and it was active within
`IDLE_TIMEOUT` (see "An idle session isn't closed by an answer"). The history lists
summaries without loading sessions, so the rule exists twice: `session_end`
(shared by `ExerciseSession.ended_at` and `SessionSummary.ended_at`) and its SQL form
in the repository's `status` filter (`finished_at IS NULL AND updated_at >= now -
IDLE_TIMEOUT`). Both take `now` from the caller, so a summary and the full session
agree on whether it's open.

## Activity per day is grouped in Python

Answers per day must follow the user's day, not UTC's. Grouping by local date in SQL
needs different time zone functions in PostgreSQL and SQLite (used in tests), so the
repository returns the window's raw `answered_at` / `is_correct` pairs
(`answers_since`) and the use case buckets them with `zoneinfo` in the requested
`tz`. The window is capped at 365 days, and every day of it is returned, empty ones
included.

## Directions are grouped as sets; most missed is split per kind

A direction's shown fields are a JSON list, and PostgreSQL can't `GROUP BY` a `json`
column. Rows are grouped by its text (`CAST(prompt_fields AS TEXT)`) and merged in
Python into `frozenset`s, so `[reading, meaning]` and `[meaning, reading]` count as one
direction. The most missed items are two methods, `most_missed_entries` and
`most_missed_kanji`, rather than one with a kind argument: entry and kanji ids come
from different tables, and a single list could mix them (see "Ports take typed
entities, not ids").

## Skipping is a miss

A question can be skipped (`{"type": "skip"}` as the answer). It's graded as wrong,
not dropped: skipping is usually "I don't know", so the item comes back as a review
like any miss, the solution is shown, and accuracy isn't inflated by leaving out the
hard cards. It's one more member of the answer union, so the next-question rules and
the statistics, which only read `is_correct`, needed no change, and there's no
separate endpoint.

## Questions are a union too, with what each type adds in one JSON column

Extends "Exercise settings are JSON behind a discriminated union" to the questions.

Every exercise type shares what statistics and the review read: the item, the prompt
and back, the answer, right or wrong, when and how long. Those stay real columns. What
only one type has (a choice card's options and right option; a handwriting card's
reference strokes and grade; later a sentence's gaps or a typed answer's accepted
values) is always read whole and never queried by its parts, so it goes in one JSON
column, `details`, next to a `type` column. The domain has one class per type
(`ChoiceQuestion`, `HandwritingQuestion`) in a union keyed by `type`, which validates
`details` on the way back.

Rejected:

- **A column per type-specific field.** Each new type would add columns that are
  empty for every other type.
- **A child table per type.** One more table, join and mapper per type, for data that
  is never queried apart.

The choice cards' `options` and `correct_option` moved into `details` (migration
`33f2afbdd7cf`), so no column is left empty.

## Handwriting questions read the dictionary when they're asked

Narrows "The dictionary is used in-process behind a port", which says the practice app
only needs the dictionary at import time.

A handwriting question needs KanjiVG's strokes of every kanji it accepts, and the pool
must leave out kanji without a stroke order. They're read from the dictionary when a
question is built (start and every answer: `literals_with_strokes` over the pool, then
`stroke_references` for the accepted kanji) and snapshotted in the question, rather
than copied into the library at import time:

- Strokes aren't the user's data: nothing in them is customised or disabled, unlike
  readings and meanings.
- Kanji imported before this feature would need a backfill, and every import would
  carry a few kilobytes most users never draw.
- The question's snapshot already keeps a session readable after the dictionary
  changes.

The cost is two in-process queries per question. With an HTTP adapter it would be
two calls per answer, which batching (both calls take many literals) keeps bounded.

## A drawing is graded by a service and recorded by the session

Grading a drawing is a sizeable algorithm (see
[exercises](exercises.md#handwriting)), so it's a domain service,
`handwriting_grading_service`, not a method of the question: entities don't depend on
services. The use case runs it on the question's references and passes the grade to
`ExerciseSession.answer`, as it passes `build_next_question`'s result to `ask`. The
session keeps the invariants: the answer must be of the question's type, a drawing
needs a grade of a kanji the question accepts, and it decides `is_correct` from the
verdict. Choice cards are still graded inline: comparing two indexes needs no service.

## A drawing "close" enough counts, and comes back

A drawing graded `close` (right kanji, but a stroke out of order, backwards, or a bit
off) counts as right, so the score and accuracy don't punish a nearly right drawing,
but its item comes back as a review like a miss (`needs_review`). The grade keeps the
verdict, so the review can show it apart.

The grading leans to the learner. Nobody writes as exactly as KanjiVG draws:
matching the stroke lengths, the place on the grid and the directions that closely is
too hard, and too strict a grader discourages beginners. So:

- **Imprecise strokes and stroke lengths** (judged by proportions, not size) are
  **warnings only**. They're shown on each stroke and lower the score, but never the
  verdict.
- **The verdict** depends on the whole drawing (the picture), the stroke order and
  direction, and the stroke count. Strokes pair with some margin, so a stroke out of
  place is imprecise rather than extra plus missing.
- **The accepted cost:** near twins that differ only in lengths or positions (未 / 末,
  土 / 士) pass for each other, with warnings. Kanji of another shape or stroke count
  still fail.

Reverses the previous rebalance, from the review of PR #60, which made length
mistakes `close` and many imprecise strokes `wrong`: trying it showed it was too
strict. A handwriting recognition model may replace this grader later. The thresholds
and their calibration are in [exercises](exercises.md#grading).

## Words are written a character per cell, in their own question type

Writing a word by hand (#67) reuses the kanji grader cell by cell rather than
grading a whole word drawn freely: cutting handwriting into characters isn't
reliable, and a cell per character gives each one its own comparison and feedback.
The cells are shown, so their number is a hint; without it the user couldn't know
where a character ends. Words of another length are therefore never accepted.

A word's verdict is its worst cell's: one wrong character makes another word. The
score is the cells' average, for the user's eyes only, as for kanji.

It's a new question type, `card.handwriting_word` with a `CellsAnswer` and a
`WordGrade`, not kanji turned into one-character words: kanji questions keep their
stored shape, so no stored JSON had to be migrated, and each player stays simple.
The exercise settings stay one type (`card.handwriting`); the direction's answer
field (`literal`, or `writing` / `reading`) says what is written. Asking for the
reading is how kana words and kana practice fit in, since KanjiVG draws every kana.

## Only another character fails a written word

Writing words (#67) showed the grader, tuned on kanji, was unfair to kana (#71):
dakuten strokes are too small to pair by shape, so べ failed; ゃ and や are the same
shape once normalized; and a kana with a stroke missing failed like a kanji does
(the "no count errors under 5 strokes" rule). With the word taking its worst cell's
verdict, one such slip failed the whole word.

Softening the word rule alone wasn't an option: たべる with ろ for る must fail. So
grading separates **which character** it is from **how well it's written**:

- Marks (dakuten, handakuten, dots) pair by position, and only missing or adding a
  whole run of them changes the character. This applies to kanji too (大 / 犬 / 太),
  but only to characters of up to 6 strokes: a review of #76 found dense kanji
  have many short strokes (9 of 識's 19), whose direction then went unchecked and
  one of which missing failed the drawing. Their direction counts too, loosely: only
  a mark turned more than 120° is `reversed`.
- Kana are recognised against every other kana; only one that fits clearly better
  makes a cell wrong, and the feedback names it. A recognised kana is at worst close.
- Small kana are told apart by size against the word's other kana, from what their
  references predict.

The word still takes its worst cell's verdict, which now only fails on a wrong
character. Recognition costs about 0.1 s per kana cell (grading against the ~180
kana); kanji aren't recognised against other kanji (too many), so they keep the
kanji rules.

## Stroke order comes from KanjiVG, without a hanzi-writer fallback

Both dictionaries draw stroke order from KanjiVG, which the dictionary database ships
in `kanji_svg`. The `shodoukan` library parses it into stroke paths in writing order,
and the APIs serve them (`/kanji/{literal}/strokes`,
`/dictionary/kanji/{literal}/strokes`). Before, the `shodoukan-ui` components used
hanzi-writer's data from a CDN. That data is Chinese, so it has no Japanese forms
(楽, 気, 図, 駅…) and it teaches the Chinese stroke order.

Coverage, measured on the 13,108 kanji of the database:

| Source | Kanji |
|---|---|
| KanjiVG | 6,417, including all 2,136 jōyō |
| + canonical form of compatibility ideographs (神 U+FA19 → U+795E) | +72 |
| + hanzi-writer as a fallback | +1,895, none jōyō; 237 appear in any word |

The fallback was left out. What it adds is rare kanji and old forms, and it brings
four problems:

- The Chinese stroke order and glyph shapes, which are wrong for a Japanese learner.
- A second rendering path: its strokes are filled outlines in a flipped 1024 box,
  while KanjiVG's are centre lines in 109.
- A runtime dependency on a CDN.
- Another licence (Arphic) to attribute.

More coverage, if needed, belongs in the `shodoukan-db` pipeline from a Japanese
source, not in the frontend. Strokes are served as JSON (paths and number positions),
not raw SVG, so the contract is typed and the frontend renders plain SVG without
parsing XML. A few KanjiVG drawings use an older component form, so their stroke count
can differ from KANJIDIC2's (108 of 6,417).

KanjiVG also draws the kana: `kanji_svg` holds all of hiragana (90) and katakana (94,
ー included), plus digits and some punctuation, and the strokes endpoints serve any
single character. Only the library is limited to KANJIDIC2's kanji.

## Writing practice is ephemeral and frontend-only

Writing practice (`/practice`) is for learning to write a kanji, before the exercises
or as a review in the middle of a session. It stores nothing: no sessions, no history,
no statistics. Those belong to the exercises, which test; mixing in drawings that were
traced over a model would skew them. With nothing to store, it needs no endpoint: the
frontend loads the strokes (`/dictionary/kanji/{literal}/strokes`) and does the rest.

For the same reason, free practice has no grade: checking lays the drawing over the
model and lets the user judge. Sending it to the grader would need a new endpoint
outside sessions, and a score while tracing over the model says little.

## Guided strokes are matched in the frontend

Guided practice judges each stroke as soon as it's drawn, so a round trip per stroke
was ruled out. `shodoukan-ui` has `pathPoints` (a port of `shodoukan`'s
`path_points`, same sampling) and `matchStroke`, which uses the grader's stroke
distance (the mean point distance and the larger end-point distance, averaged, over 16
resampled points) with two differences:

- The distance is in absolute KanjiVG units, not normalised by the drawing's box:
  the stroke is traced on the model's own canvas, so where it lies matters.
- It compares one stroke with the one expected next, so there is no pairing or order
  check. A stroke that matches backwards is flagged as such.

The threshold (`GUIDED_STROKE_MATCH`, 0.12 of the square, about 13 units) is its
own, tuned by hand. The two implementations can drift apart; if guided practice ever
needs to agree with the exercises' verdicts, the grader should be the reference.

## Sources are credited once, on an About page

The data licences (CC BY-SA for JMdict, KANJIDIC2, RADKFILE and KanjiVG; CC BY for
Tatoeba and the JLPT lists) ask for attribution "in any reasonable manner" for the
medium, not next to every item. Both apps credit every source on one About page, the
shared `AboutSources` from `shodoukan-ui`, linked from the practice sidebar and the web
navbar. Data screens carry no per-item credit lines. A new data source is added to
`AboutSources`, with its author, link and licence checked at its origin (the
shodoukan-db README only states JMdict's and KANJIDIC2's).

## Deployment split: dictionary on Render, practice self-hosted

Everything has to run for free, with no card and no paid domain. The dictionary (API
and web) is public, read-only and stateless, so it stays on Render's free tier: public
traffic and crawlers never reach our machine, and it's up when that machine is off.
The practice stack needs PostgreSQL and Keycloak (about 1 GB of RAM), and no free host
fits that: Render's free Postgres expires after 30 days and its 512 MB instances sleep,
and Fly.io no longer has a free tier. It runs with docker compose on a machine of ours
instead. It doesn't depend on Render, because it reads the dictionary in-process (see
"The dictionary is used in-process behind a port"). Rejected: everything self-hosted,
which would put public dictionary traffic on a home PC; an Oracle Cloud free VM, which
needs a card. Details: [deployment](../../technical/deployment.md).

## Tailscale Funnel with path routing, Keycloak at /idp

The self-hosted stack is published with Tailscale Funnel: an outbound tunnel that
needs no router ports, works behind CGNAT, includes HTTPS and is free without a card.
Funnel gives one hostname, so Caddy routes by path: `/` (SPA), `/practice-api/`, `/idp/`.
Everything is same-origin, so CORS is never needed and one SPA build works on any
host. Keycloak is at `/idp`, not `/auth`, because the SPA's own `/auth/callback` route
would sit under the same prefix. Rejected: DuckDNS with router port forwarding, which
fails behind CGNAT and exposes the home IP.

## The dictionary is baked into images and refreshed monthly

Both APIs download the dictionary SQLite at image build time instead of loading it at
runtime. It only changes with the monthly `shodoukan-db` release, so there's nothing to
reload in between. Images stay immutable: rolling back an image rolls back the data
too, nothing downloads at container start, and the file stays read-only. A scheduled
workflow rebuilds both on the 2nd of each month.

## Frontends are static SPAs

The dictionary frontend was rendered on the server, but its pages fetch data in
watchers that SSR doesn't await, so the server only produced a "loading" page.
Switching it to `ssr: false` loses nothing. Both apps are now generated as static
files: the dictionary on a Render Static Site, which doesn't use the 750 free instance
hours and never sleeps, and the practice SPA served by Caddy. No Node process runs in
production. On the free tier, SSR would mean a second web service, which would exhaust
the instance hours and add a second cold start.

## Practice deploys are pulled by hand

CI builds and publishes the practice images to GHCR, and the host deploys them with
`deploy/deploy.sh`. A self-hosted GitHub runner on the host would deploy automatically,
but it runs repository code on a personal machine of a public repo. We deferred it:
adding one later only means a job that calls the same script.

## One pre environment, shared through a private Tailscale tunnel

Reverses "Tailscale Funnel with path routing" (the path routing stays) and "Practice
deploys are pulled by hand".

Until the app is deployed anywhere, everything served from this machine is pre. Running
a pre and a prod side by side on one PC was ceremony, so there's one self-hosted
environment. Friends use it, so it must be stable and keep their data.

- `deploy/deploy.sh` builds a commit (default `origin/main`) in a separate git
  worktree, so pre only runs committed code and the working checkout is never touched.
- It backs up both databases before every deploy, and `seed` asks before replacing
  data.
- Images are built on the host. Publishing them to GHCR from CI added a workflow and
  public packages for one consumer; any git ref deploys or rolls back just as well.

Access is private. `tailscale serve`, without Funnel, makes the stack reachable only
from our tailnet and from the people we share the `shodoukan` node with. They install
the free Tailscale app on a phone or computer. The node is its own container, so
sharing it exposes nothing else of the machine. On top of that, the realm is
invite-only.

Rejected:

- **Funnel with closed registration.** No app to install, but the login page would be
  public.
- **Cloudflare Tunnel with Access.** It needs a paid domain.

## Own senses start with a meaning; a disabled sense keeps its parts' flags

Narrows "Dictionary data in the library is only ever disabled": senses now have an
`origin` and an `enabled` flag too.

- A sense of the user's own is created with its first meaning (`POST .../senses` takes
  the gloss), so a new sense never shows up empty and doesn't need its own fields:
  `pos` / `misc` stay empty, and its content is its meanings, examples and note.
- Only own senses are removed, with their meanings and examples. Imported senses are
  only disabled, and still take the user's own meanings.
- Disabling a sense doesn't touch the flags of its glosses and examples: whether a gloss
  counts is `sense.enabled and gloss.enabled`. Re-enabling the sense brings it back
  exactly as it was, and there's one write per toggle.

## Own examples are a sentence and one translation at a time

An own example has the shape of JMDict's (a sense's example, one sentence per
language), so the views, the toggles and a future re-sync treat both alike. The user
writes the Japanese sentence and, optionally, its translation in the language they're
reading in; editing touches only that language and keeps translations written in
others, so switching language never loses one. `text` (JMDict's form of the word in the
sentence) stays empty: nothing shows it, and asking for it would only slow the user down.
