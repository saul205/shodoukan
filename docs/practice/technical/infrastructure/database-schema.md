# Database Schema

[← Technical documentation](../README.md)

Tables, constraints and cascades of the practice database. The engine is
**PostgreSQL**; unit tests run on SQLite, so only portable column types are used.
The models that define these tables are described in
[ORM and mappers](orm-and-mappers.md).

## Tables

| Table | Parent | Constraints and notes |
|---|---|---|
| `users` | — | `id` **`uuid`**: the identity provider's user id (token `sub`), not generated here; `username` (display name, up to 255 characters, not unique) |
| `practice_entries` | `users` | `source_entry_id` nullable (a word of the user's own has none), `UNIQUE(user_id, source_entry_id)` (NULLs are distinct, so own words can repeat), `notes` text (nullable), `original_id`, `source_id`, `dismissed_parts` JSON (default `[]`) |
| `practice_entry_kanji_readings` | `practice_entries` | `position`, `info` JSON, `enabled`, `origin` (CHECK), `original_id`, `source_id`, `edited_id`, `revision` (default 0), `source_collection_ids` JSON (default `[]`) |
| `practice_entry_readings` | `practice_entries` | `position`, `info` / `restricted_to` JSON, `enabled`, `origin` (CHECK), `original_id`, `source_id`, `edited_id`, `revision` (default 0), `source_collection_ids` JSON (default `[]`) |
| `practice_senses` | `practice_entries` | `position`, `pos` / `misc` / `dialects` / `info` JSON, `notes` text (nullable), `enabled`, `origin` (CHECK), `original_id`, `source_id` |
| `practice_glosses` | `practice_senses` | `position`, `enabled`, `origin` with `CHECK origin IN ('imported','added')`, `original_id`, `source_id`, `edited_id`, `revision` (default 0), `source_collection_ids` JSON (default `[]`) |
| `practice_examples` | `practice_senses` | `position`, `enabled`, `origin` (CHECK), `original_id`, `source_id`, `edited_id`, `revision` (default 0), `source_collection_ids` JSON (default `[]`) |
| `practice_example_sentences` | `practice_examples` | `position`, `lang`, `text` |
| `practice_sentences` | `users` | `text` (the Japanese), `is_active`, `notes` text (nullable), `origin` (CHECK), `original_id`, `source_id`, `edited_id`, `revision` (default 0), `source_collection_ids` JSON (default `[]`). Converted from `practice_examples`, keeping their ids |
| `practice_sentence_translations` | `practice_sentences` | `position`, `lang`, `text` |
| `practice_sentence_words` | `practice_sentences` | `position`, `span_start` / `span_end` (both or neither: `CHECK span_complete`), `lemma`, `reading`, `pos` JSON (default `[]`), `inflection_endings` JSON (NULL: not analyzed), `inflection_form`; `entry_id` → `practice_entries` and `sense_id` → `practice_senses`, both nullable and `SET NULL` (index on `entry_id`: the sentences of a word) |
| `practice_kanji` | `users` | `UNIQUE(user_id, literal)`, `notes` text (nullable), `dismissed_parts` JSON (default `[]`) |
| `practice_kanji_reading_items` | `practice_kanji` | `kind` with `CHECK kind IN ('on','kun','nanori')`, `position`, `enabled` |
| `practice_kanji_meanings` | `practice_kanji` | `position`, `enabled`, `origin` (CHECK), `original_id`, `source_id`, `edited_id`, `revision` (default 0), `source_collection_ids` JSON (default `[]`) |
| `entry_collections` | `users` | `UNIQUE(user_id, name)`; `is_public` (default false), `published_version` (default 0), `published_at`; `source_collection_id`, `source_version` |
| `kanji_collections` | `users` | `UNIQUE(user_id, name)`; `is_public` (default false), `published_version` (default 0), `published_at`; `source_collection_id`, `source_version` |
| `entry_collection_items` | link table | PK `(collection_id, entry_id)`, index on `entry_id`, `added_at`, `from_source` (default false) |
| `entry_collection_publications` | `entry_collections` | PK `collection_id` (one row per collection: the latest version), `item_count`, `includes_notes`, `payload` JSON (a `SharedEntryCollection`) |
| `entry_collection_downloads` | link table | PK `(collection_id, user_id)` (one row per user), index on `user_id`, `version` (the latest imported), `downloaded_at` |
| `entry_collection_dismissed_items` | `entry_collections` | PK `(collection_id, item_key)`: the shared keys of the items the user took out of a copy |
| `kanji_collection_items` | link table | PK `(collection_id, kanji_id)`, index on `kanji_id`, `added_at`, `from_source` (default false) |
| `kanji_collection_publications` | `kanji_collections` | PK `collection_id` (one row per collection: the latest version), `item_count`, `includes_notes`, `payload` JSON (a `SharedKanjiCollection`) |
| `kanji_collection_downloads` | link table | PK `(collection_id, user_id)` (one row per user), index on `user_id`, `version` (the latest imported), `downloaded_at` |
| `kanji_collection_dismissed_items` | `kanji_collections` | PK `(collection_id, item_key)`: the shared keys of the items the user took out of a copy |
| `exercises` | `users` | `item_kind` with `CHECK item_kind IN ('entries','kanji')`, `settings` JSON, `name` (not unique), `description` |
| `exercise_entry_collections` | `exercises` | PK `(exercise_id, collection_id)`, `collection_id` → `entry_collections`, index on `collection_id`, `position` |
| `exercise_sessions` | `users` | partial unique index `uq_exercise_sessions_user_id_open` on `user_id` `WHERE finished_at IS NULL` (one open session per user); `exercise_id` → `exercises` (`SET NULL`), `exercise_name`, `item_kind` (CHECK), `meaning_lang`, `finished_at` (nullable) |
| `exercise_questions` | `exercise_sessions` | `position`, `UNIQUE(session_id, position)`; `entry_id` → `practice_entries` / `kanji_id` → `practice_kanji`, both `SET NULL`, `CHECK entry_id IS NULL OR kanji_id IS NULL`; `type` (`CHECK` `card.choice` / `card.handwriting` / `card.handwriting_word`); `prompt_fields`, `prompt`, `back`, `answer` JSON; `details` JSON, what only the type has (choice: `options`, `correct_option`; handwriting: `references`, `grade`; word handwriting: `words`, `grade`); `is_correct`, `answered_at`, `response_ms` |
| `exercise_kanji_collections` | `exercises` | PK `(exercise_id, collection_id)`, `collection_id` → `kanji_collections`, index on `collection_id`, `position` |

`original_id`, `source_id`, `edited_id`, `source_collection_ids` and the collections'
`source_collection_id` (nullable integers or, for `source_collection_ids`, a JSON list;
**no foreign keys**) record where an imported copy came from: the part all its copies
share, the row it was copied from, the version of its content (`NULL` is the row
itself), and the collections that bring it. The origin may be another user's and be
gone. See
[importing a collection](../../proposals/library-authoring-and-sharing.md#importing-a-collection-86-from-a-file-82-from-another-user).

Every table except `users` and the link tables has an integer `id` primary key.
`users.id` is a UUID, and so is every `user_id` foreign key (`practice_entries`,
`practice_kanji`, `entry_collections`, `kanji_collections`, `exercises`). SQLAlchemy's `Uuid` type is
native `uuid` on PostgreSQL and `CHAR(32)` on SQLite. Aggregate tables
(`users`, `practice_entries`, `practice_kanji`, `*_collections`, `exercises`,
`exercise_sessions`) have
`created_at` and `updated_at`. The exercise link tables have no `id`: their primary key
is the pair of foreign keys.

## Cascades

- Every foreign key uses `ON DELETE CASCADE`, except the ones that keep exercise
  history: `exercise_sessions.exercise_id` and `exercise_questions.entry_id` /
  `kanji_id` are `SET NULL`, so sessions outlive their exercise and items. And a
  sentence's words: `practice_sentence_words.entry_id` / `sense_id` are `SET NULL`,
  so removing a word (or an own sense) from the library leaves its sentences, with
  the gap unlinked.
- Deleting a user removes their whole library, their collections and all links.
- Deleting an entry or kanji removes its nested rows and its links; the collections
  stay.
- Deleting a collection removes its links, including its links to exercises; the items
  and the exercises stay.
- Deleting an exercise removes its collection links; the collections stay.

## Conventions

- **Order.** Nested lists keep their order in a `position` column (0-based).
- **Lists of strings** are `JSON` columns (portable; not `JSONB`).
- **Session answers** are SQL `NULL` until given (`JSON(none_as_null=True)`), so
  statistics can filter on them.
- **Exercise settings** are one `JSON` column, read and written whole and validated by
  the domain (see [exercises](../exercises.md#storage)).
- **User notes** are nullable `TEXT` with no length limit in the database; the domain
  caps them at 2000 characters and stores a blank note as `NULL`.
- **Dates** are `timestamp without time zone` holding UTC, with no database default.
  See [dates and time zones](../cross-cutting/dates-and-time-zones.md).
- **Other defaults** (`enabled`, `is_active` → true, `origin` → `'imported'`) are set
  both on the ORM and as `server_default`, so raw SQL inserts get them too.
- **Constraint names** are deterministic (`pk_<table>`, `fk_<table>_<col>_<ref>`,
  `uq_<table>_<cols>`, `ck_<table>_<name>`, `ix_<table>_<col>`), set by the naming
  convention on `Base`. This lets Alembic alter and drop constraints reliably.
- Enum-like strings use a named `CHECK` constraint rather than a database enum type,
  which keeps them portable and easy to extend with a migration.
