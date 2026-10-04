# Domain Entities

[← Technical documentation](../README.md)

The aggregates of the practice domain, their state and the rules for changing them.
Code: `src/shodoukan_practice/domain/entities/`.

## Aggregates

All entities are Pydantic models. Aggregate roots inherit
[`TimestampedEntity`](#timestamps-and-touch).

| Aggregate | Module | Key fields |
|---|---|---|
| `User` | `user_entity.py` | `id: UUID`, the identity provider's user id (the token's `sub`), so practice users map 1:1 to provider users; `username` (display name from the provider, not unique) |
| `PracticeEntry` | `practice_entry_entity.py` | `user_id` (UUID), `source_entry_id`, `kanji_readings`, `readings`, `senses` → `glosses`, `examples` → `sentences`, `jlpt`, `is_common`, `is_active`, `notes`; each sense has its own `notes` |
| `PracticeKanji` | `practice_kanji_entity.py` | `user_id`, `literal`, `on_readings`, `kun_readings`, `nanori`, `meanings`, `grade`, `stroke_count`, `freq`, `jlpt`, `is_active`, `notes` |
| `Collection` → `EntryCollection`, `KanjiCollection` | `collection_entity.py` | `user_id`, `name` (1–100 characters, `COLLECTION_NAME_MAX_LENGTH`, unique per user and kind), `description` |
| `Exercise` → `EntryExercise`, `KanjiExercise` | `exercise_entity.py` | `user_id`, `name` (1–100, `EXERCISE_NAME_MAX_LENGTH`, not unique), `description`, `collection_ids`, `settings`; `item_kind` (`"entries"` / `"kanji"`) comes from the subclass |

Everything is re-exported from `domain/entities/__init__.py`.

## Snapshot and practice state

A `PracticeEntry` / `PracticeKanji` is a copy of the dictionary item taken at import
time, so dictionary updates never overwrite the user's edits. The only link back is
`source_entry_id` (shodoukan `Entry.id`) or `literal` (shodoukan `Kanji.literal`).

On top of the snapshot:

- `enabled: bool` on readings, kanji spellings, glosses, examples, kanji reading items
  and kanji meanings: the user can hide individual parts.
- `origin: "imported" | "added"` on glosses, examples and kanji meanings: the user can
  add their own, and they stay distinguishable from imported ones.
- `notes` on the entry, on each of its senses, and on the kanji: the user's own
  free text (`Notes` in `notes_value.py`: stripped, blank becomes `None`, at most
  2000 characters).
- `is_active` on the aggregate: an inactive item stays in the library and in its
  collections, but is skipped when listing a collection's cards and when building
  exercise pools.

`PracticeKanjiReading` (a word's kanji spelling, e.g. 食べる) isn't the same as
`PracticeReadingItem` (one on/kun reading or nanori of a character).

## Collections

- **Metadata only.** A collection holds its name and description, not its members.
  Membership lives in link tables and is read and changed through the
  [collection repositories](repository-ports.md#collection-repositories), so listing
  cards paginates in SQL and tagging one item never loads the whole membership.
- **Collections double as tags.** Tagging an item "verbs" means adding it to the
  "verbs" collection. There is no separate Tag entity.
- **Entry and kanji collections are separate subclasses** and never mixed. Code that
  only needs the grouping (e.g. exercises) works against the `Collection` base.
  Why subclasses: [decisions](../decisions.md#entry-and-kanji-collections-are-subclasses).

## Exercises

A saved exercise. The design (types, sessions, statistics) is in
[exercises](../exercises.md); this is what's built.

- **Subclasses by item kind.** `EntryExercise` studies the fields `writing`,
  `reading`, `meaning` (`ENTRY_FIELDS`); `KanjiExercise` studies `literal`, `onyomi`,
  `kunyomi`, `meaning` (`KANJI_FIELDS`). A model validator rejects settings that use a
  field of the other kind, on construction and on `configure`.
- **`settings: ExerciseSettings`**, for now only `ChoiceCardSettings`
  (`type = "card.choice"`): `directions`, `back_fields`, `option_count` (2–8, default
  4), `distractor_source` (`"collection"`), `question_count` (1–200 or `None` for
  every item, default 10). Frozen value objects. `ExerciseSettings` becomes a union
  discriminated by `type` when a second exercise type is added; card types share
  `CardSettings` (`directions`, `back_fields`).
- **`Direction(prompt, answer)`**: the fields shown (at least one, no repeats) and the
  field asked, which can't be one of them. An exercise needs at least one direction
  and can't repeat one (the prompt's order doesn't count); back fields can't repeat.
- **`collection_ids`**: the collections it draws from, in order. They're part of the
  definition, so the entity holds them (unlike a collection's members). It can be
  empty after its collections are deleted: the exercise stays but can't run. Why:
  [decisions](../decisions.md#an-exercise-holds-its-collection-ids).

## Timestamps and `touch()`

`TimestampedEntity` (`timestamped_entity.py`):

- `created_at` / `updated_at` default to `utc_now()` (aware UTC). See
  [dates](../cross-cutting/dates-and-time-zones.md).
- `touch()` sets `updated_at = utc_now()`.
- `validate_assignment=True`: assignments made by methods are validated like the
  constructor (e.g. `rename("")` fails).

**Rule: aggregates change only through their own methods, and every method that
changes state calls `touch()`.** A call that changes nothing doesn't touch. Use cases
call methods; they don't assign fields of a loaded aggregate.

Current methods:

| Aggregate | Methods |
|---|---|
| `Collection` | `rename(name)`, `describe(description)` |
| `Exercise` | `rename(name)`, `describe(description)`, `configure(settings)`, `use_collections(collection_ids)` (keeps order, drops duplicates) |
| `PracticeEntry`, `PracticeKanji` | `activate()`, `deactivate()`, `set_notes(notes)`, `set_enabled(part, item_id, enabled)` |
| `PracticeEntry` | `set_sense_notes(sense_id, notes)`, `add_gloss(sense_id, text, lang)`, `edit_gloss(gloss_id, text)`, `remove_gloss(gloss_id)` |
| `PracticeKanji` | `add_meaning(text, lang)`, `edit_meaning(meaning_id, text)`, `remove_meaning(meaning_id)` |

`part` is an `EntryPart` (`"kanji_readings"`, `"readings"`, `"glosses"`, `"examples"`)
or a `KanjiPart` (`"readings"`, covering on, kun and nanori, or `"meanings"`). A nested
id that isn't there raises `EntityNotFoundError`. Nested models don't validate on
assignment, so notes go through `parse_notes` and meaning texts through
`clean_meaning` (`nested_item_lookup.py`).

## Customisation rules

The library copy keeps the dictionary's data intact; the user layers their choices on
top:

- **Dictionary data is never edited or deleted, only disabled.** That covers every
  reading, spelling, example and imported (`origin="imported"`) meaning. Editing or
  removing an imported meaning raises `OriginalDataError`.
- **Meanings are an editable list.** The user adds meanings of their own
  (`origin="added"`, appended to the sense or kanji) and can edit their text or remove
  them. Entry glosses use ISO 639-2 language codes (`eng`), kanji meanings ISO 639-1
  (`en`), as the dictionary stores them.
- **Readings can't be added** for now, only disabled. They have no `origin` column.
- **Notes**: one general note on the entry or kanji, plus one per sense.

Why: [decisions](../decisions.md#dictionary-data-in-the-library-is-only-ever-disabled).
