# shodoukan-practice

Practice/exercises backend: each user's library of imported entries and kanji, and
their collections. Follows the `python-backend-clean-code` skill fully. This file holds
the package's specifics. The full technical reference is in
[`docs/practice/technical/`](../../docs/practice/technical/README.md); read the page
for the area you're touching, and update it in the same commit (see the "where to
document what" table there).

## Status

Built: domain, PostgreSQL persistence (ORM, Alembic), mappers, SQLAlchemy repositories,
the dictionary integration (in-process `shodoukan` library behind `DictionaryGateway`),
sign-in through Keycloak (users auto-created on first request, `GET /users/me`), importing an entry or kanji (`POST /library/entries`, `POST /library/kanji`), and public
dictionary search (`GET /dictionary/search`, same `Dictionary.search` as shodoukan-api),
the import status of search results (`GET /library/imported`), listing and searching
the library (`GET /library/entries`, `GET /library/kanji`, paged with a total; `q`,
`meaning_lang`, `not_in_collection`), and collections
(`/collections/entries`, `/collections/kanji`: CRUD plus adding, removing and paging
items), dictionary entry and kanji details (`/dictionary/entries/{id}`,
`/dictionary/kanji/{literal}`, ...), and customising library items (notes, enabling
parts, own meanings, active, removal: `/library/entries/{id}/...`,
`/library/kanji/{id}/...`), saved exercise definitions (`/exercises`: CRUD) and
exercise sessions (`POST /exercises/{id}/sessions`, `/exercise-sessions/{id}` with
`/answer` and `/finish`: open-ended, one active question at a time, built and graded
on the server; choice cards, kanji handwriting and words written a character per
cell, graded against KanjiVG strokes), the session history (`GET /exercise-sessions`, summaries without
questions) and statistics (`GET /exercises/{id}/statistics`, `GET /statistics`: SQL
aggregates over the answered questions, computed on request); design in
`docs/practice/technical/exercises.md`. The practice and dictionary apps are
standalone: never call shodoukan-api from here.

## Layout

`src/shodoukan_practice/`:

- `domain/`
  - `entities/`: `practice_entry_entity.py`, `practice_kanji_entity.py`,
    `user_entity.py`, `collection_entity.py`, `exercise_entity.py`,
    `exercise_session_entity.py`, and `timestamped_entity.py` (`TimestampedEntity`
    with `touch()`).
  - `repositories/`: Protocol ports. Read models live with their port:
    `SessionSummary` in `exercise_session_repository.py`; `AnswerTotals`,
    `DirectionTotals`, `ItemTotals`, `ExerciseTotals`, `AnswerMoment` with the
    read-only `ExerciseStatisticsRepository` in `exercise_statistics_repository.py`.
  - `gateways/dictionary_gateway.py`: `DictionaryGateway`, the read-only dictionary port;
    `gateways/kana_gateway.py`: `KanaGateway` (romaji/kana → both kana scripts).
  - `searches/library_search.py`: library search criteria, match tiers and scopes.
  - `services/collection_service.py`: `ensure_combinable`;
    `services/study_field_service.py` (field values, comparison keys, `entry_label`) and
    `services/question_order_service.py` (which item comes next, the card's front and
    back; shared by every card type), `services/choice_question_service.py`
    (`build_next_question`: the distractor rule), and for handwriting
    `services/handwriting_question_service.py` (`draft_next_question`),
    `services/stroke_geometry_service.py` and `services/handwriting_grading_service.py`
    (`grade_drawing`); for words, `services/word_handwriting_question_service.py`
    (`draft_next_word_question`) and `services/word_grading_service.py` (`grade_word`;
    kana recognised by `grade_kana`, small kana by size).
  - `exceptions.py`, and `clock.py` with `utc_now()`.
- `infrastructure/db/`
  - `orm/`: `base_orm.py` (`Base`, `UtcDateTime`, `children()`) plus one `*_orm.py`
    per aggregate.
  - `mappers/`, `migrations/`, `connection.py`.
- `application/commands/library_commands.py`: `ImportEntry`, `ImportKanji`
  (idempotent, return `ImportResult(item, created)`), `CreateOwnEntry`.
- `application/commands/user_commands.py`: `EnsureUser` (creates the user on first use).
- `application/commands/practice_entry_commands.py` / `practice_kanji_commands.py`:
  customising one library item (`SetEntryNotes`, `SetEntryPartEnabled`,
  `AddKanjiMeaning`, `RemoveEntryFromLibrary`, ...). Routes in
  `api/routes/practice_entry_routes.py` / `practice_kanji_routes.py`.
- `application/commands/collection_commands.py` / `queries/collection_queries.py`:
  collection use cases, one class per use case and kind (`CreateEntryCollection`,
  `AddKanjiToCollection`, ...).
- `application/commands/exercise_commands.py` / `queries/exercise_queries.py`:
  `CreateExercise`, `UpdateExercise`, `DeleteExercise`, `ListExercises`, `GetExercise`.
  Routes in `api/routes/exercise_routes.py`.
- `application/commands/exercise_session_commands.py` /
  `queries/exercise_session_queries.py`: `StartExerciseSession`,
  `AnswerExerciseQuestion` (grades and asks the next; both take an optional
  `random.Random`), `FinishExerciseSession`, `GetExerciseSession`,
  `ListExerciseSessions` (the history, `SessionSummaryPage`). Routes in
  `api/routes/exercise_session_routes.py`.
- `application/queries/exercise_statistics_queries.py`: `GetExerciseStatistics`,
  `GetPracticeStatistics` (activity per day bucketed in Python in the user's time
  zone), `MissedItem` (named from the current library item). Routes in
  `api/routes/exercise_statistics_routes.py`, schemas in
  `api/schemas/exercise_statistics_schemas.py`.
- `application/queries/library_search_queries.py`: `SearchEntries`, `SearchKanji`
  (every list of library items: the library, a collection's items, the picker; return
  `LibraryPage(items, total, limit, offset)`), `build_search`, `resolve_scope`.
  `domain/searches/library_search.py` holds what they run: `LibrarySearch`,
  `MatchTier` and the scopes; the item repositories' `find` / `count` run it.
- `application/queries/library_queries.py`: `GetImportStatus`, `LibraryPage`,
  `GetLibraryEntry`, `ListCollectionsOfEntry` (and kanji);
  `queries/dictionary_queries.py`: `SearchDictionary`, `GetDictionaryEntry`,
  `GetDictionaryKanji`, `ListEntriesForKanji`, `ListKanjiForEntry`.
- Dictionary read models (`DictionaryEntry`, `DictionarySearchResult`, ...) live with
  the port in `domain/gateways/dictionary_gateway.py`.
- `api/`: `app.py` (maps `EntityNotFoundError` → 404, `CollectionNameTakenError` →
  409, `QuestionNotActiveError` / `SessionFinishedError` → 409, `ExercisePoolTooSmallError` /
  `InvalidAnswerError` / Pydantic `ValidationError` from a use case → 422), `auth.py`
  (`TokenVerifier`), `deps.py` (one session per request; routes commit),
  `routes/*_routes.py`, `schemas/*_schemas.py`.
- `infrastructure/repositories/`: `sqlalchemy_*_repository.py`.
- `infrastructure/dictionary/`: `ShodoukanDictionaryGateway` and `shodoukan_mapper.py`
  (the anti-corruption layer), and `ShodoukanKanaGateway`. Wired in `api/deps.py` (cached `Dictionary()`).

## Domain rules specific to this app

- Entry and kanji collections are separate subclasses (`EntryCollection`,
  `KanjiCollection`) and never mixed. Ports take the typed collection, never an id.
- Collections are metadata only. Membership lives in `entry_collection_items` /
  `kanji_collection_items` and goes through the collection repositories.
- Every query is scoped to `user_id`. `update()` raises `EntityNotFoundError` for a
  missing or foreign row; the API answers 404 for both.
- Collection names: 1–100 characters, unique per user and kind. The repository turns
  the unique-constraint violation into `CollectionNameTakenError` (savepoint).
- `User.id` **is** the identity provider's user id (the token's `sub`, a UUID); every
  `user_id` is a `UUID`. Users are created on their first request. A non-UUID `sub` →
  401. `username` is a display name, not unique.
- Migrations are append-only from now on (the pre-deploy history was squashed into one
  initial migration).
- Imports keep every language. Importing again returns the existing copy (`200`);
  `add_if_absent` uses a savepoint to handle concurrent duplicates.
- Mutating methods: `Collection.rename` / `describe`; `PracticeEntry` /
  `PracticeKanji`: `activate` / `deactivate`, `set_notes`, `set_enabled(part, id, …)`,
  words of the user's own (`PracticeEntry.create_own`, no `source_entry_id`), own
  spellings and readings (`add_spelling` / `remove_spelling`, `add_reading` /
  `remove_reading`), own senses (`add_sense` / `remove_sense`), own meanings (`add_gloss` /
  `edit_gloss` / `remove_gloss`, `add_meaning` / ...), own examples (`add_example` /
  `edit_example` / `remove_example`),
  `PracticeEntry.set_sense_notes`; `Exercise.rename` / `describe` / `configure` /
  `use_collections`. Each calls `touch()` only on a real change.
- Exercises are `EntryExercise` / `KanjiExercise` (one `exercises` table, `item_kind`);
  the subclass decides which fields its settings may use. `settings` is JSON validated
  by the domain (`ChoiceCardSettings`, keyed by `type`). `collection_ids` lives on the
  entity and is stored in one link table per kind; collection ids are looked up among
  the user's collections of the exercise's kind.
- Exercise sessions (`ExerciseSession`) are open-ended: one active question
  (`current`) plus the answered ones (`history`), the statistics store; each question
  is a snapshot (prompt, options, back) plus the answer. The next item comes from the
  history (missed items back after `REVIEW_GAP`, then a deck per round). One open session
  per user (starting one closes the other; user row lock + partial unique index); it
  ends when finished, when another starts, or after 30 idle minutes. Answers and
  finish lock the session row (`get_for_update`). Sessions and questions outlive
  their exercise and items (`SET NULL`). A distractor is never a valid answer (see
  `choice_question_service`); a word is asked by its first enabled spelling/reading.
  Unanswered questions hide their solution in the API.
- Questions are a union by `type` (`ChoiceQuestion`, `HandwritingQuestion`,
  `WordHandwritingQuestion`), stored
  with what only the type has in `exercise_questions.details`. A drawing is graded by
  `grade_drawing` (a domain service) in the use case and passed to
  `ExerciseSession.answer(..., grade=...)`; entities never call services. Handwriting
  only asks kanji with a KanjiVG stroke order (the gateway says which), accepts any
  pool kanji that fits the prompt, and snapshots their strokes (with points) in the
  question. A "close" drawing counts as right but comes back as a review. Entry
  exercises write a word (spelling or reading) a character per cell: only words whose
  every character has a stroke order, graded per cell (`grade_word`, worst cell wins).
- Dictionary data in the library is never edited or deleted, only disabled
  (`OriginalDataError` → 409); only the user's own spellings, readings, senses,
  meanings and examples change. A disabled sense hides its glosses and examples (a
  gloss counts when `sense.enabled and gloss.enabled`). A word keeps one reading
  (`LastReadingError` → 409), and a sense one meaning (`LastMeaningError` → 409), all in
  one language (`SenseLanguageError` → 422). A word of the user's own (`POST /library/entries/own`)
  has `source_entry_id = None` and only `added` parts. Notes: entry, sense and kanji
  (`Notes`, ≤ 2000 chars, blank → `None`).

## Database

- **PostgreSQL** in every real environment; unit tests use in-memory SQLite.
- URL: `PRACTICE_DATABASE_URL` (required, no default). Local values in `.env.dev`,
  documented in `.env.example`.
- Local database: `docker compose up -d practice-db`, then export the env file
  (`set -a; . ./.env.dev; set +a`).
- Migrations, run from the repo root:

  ```bash
  alembic -c packages/shodoukan-practice/alembic.ini revision --autogenerate -m "Describe the change"
  alembic -c packages/shodoukan-practice/alembic.ini upgrade head
  alembic -c packages/shodoukan-practice/alembic.ini check
  ```

## Auth (Keycloak)

- Local identity provider: `docker compose up -d keycloak` (it starts its own
  `keycloak-db`; env in `.env.keycloak`, from `.env.keycloak.example`). The realm is
  `docker/keycloak/realm-shodoukan.json`: clients `shodoukan-web` (PKCE; frontend and
  Swagger) and `shodoukan-dev-cli` (password grant, local only), user `dev`/`dev`.
- API env (`.env.dev`): `AUTH_ISSUER=http://localhost:8080/realms/shodoukan`,
  `AUTH_AUDIENCE=shodoukan-practice`.
- Run: `uvicorn shodoukan_practice.api.app:app --port 8001 --reload`; `/docs` has
  **Authorize** (Keycloak login).
- VS Code: the **Practice API** launch configuration starts the services, migrates
  (task `practice: prepare`) and runs the API with the debugger.
- Token for scripts: `curl -s -X POST http://localhost:8080/realms/shodoukan/protocol/openid-connect/token -d grant_type=password -d client_id=shodoukan-dev-cli -d username=dev -d password=dev`.
- Details: `docs/practice/technical/api/authentication.md`.

## Tests

- `pytest tests/shodoukan-practice` (domain + infrastructure).
- `tests/shodoukan-practice/conftest.py` (the only conftest; mypy rejects duplicate
  module names): SQLite engine with FKs on, savepoint-safe, cross-thread for
  `TestClient`. Fixtures: `engine`, `session`, `user`, `other_user`, `dictionary`,
  `signing_key`, `make_token`, `verifier`, `client`.
- Helpers next to it: `factories.py` (`make_entry`, `make_kanji`, `make_*_collection`,
  `NOW`, `TIMESTAMPS`) and `tokens.py` (`ISSUER`, `bearer`).
- The `dictionary` fixture is a real `shodoukan.Dictionary` seeded from the core
  `tests/db_helpers.py`.
- Layout: `domain/`, `application/`, `infrastructure/`, `api/`.
- `infrastructure/test_migrations.py` is the migration drift test. CI also runs the
  migrations on a throwaway PostgreSQL.
