# Proposal: own library content and shared collections

> **Status: proposal, not implemented** (agreed 2026-10-08). As each part is built, it
> moves to the real docs ([entities](../technical/domain/entities.md),
> [decisions](../technical/decisions.md), [customise](../functional/library/customise.md))
> and leaves this page, which ends up holding only shared collections.

Issues: #79 own senses (parent), #80 own example sentences and #81 entries from scratch
(both branch from #79, independent of each other), #86 export and import collections
as files, then #82 import public collections (future, branches from #86).

## Own senses (#79)

Built: see [entities](../technical/domain/entities.md#customisation-rules) and
[decisions](../technical/decisions.md#own-senses-start-with-a-meaning-a-disabled-sense-keeps-its-parts-flags).

## Own example sentences (#80)

Built: see [entities](../technical/domain/entities.md#customisation-rules) and
[decisions](../technical/decisions.md#own-examples-are-a-sentence-and-one-translation-at-a-time).

## Entries from scratch (#81)

Built: see [entities](../technical/domain/entities.md#snapshot-and-practice-state),
[decisions](../technical/decisions.md#words-of-the-users-own-have-no-source-readings-can-be-added)
and [creating words of your own](../functional/library/create.md).

## Importing a collection (#86 from a file, #82 from another user)

**#86 built:** export and import as files, see
[managing collections](../functional/collections/manage.md#exporting-and-importing),
[entities](../technical/domain/entities.md#sharing-shared_collection_valuepy),
[endpoints](../technical/api/endpoints.md#export-and-import) and
[decisions](../technical/decisions.md#exported-collections-are-references-plus-the-users-own-data).
The contract stays here for #82.

Importing a collection exported to a file (#86, built first) and importing a public
collection (#82) are **one use case with two sources**. The file is the payload a public
collection will be read as, so what follows is the contract for both. Agreed
2026-10-09.

### What a collection carries

For each item, its **reference plus the user's own data**, never the dictionary data
itself:

- The dictionary reference: `source_entry_id` for a word, `literal` for a kanji. On
  import the snapshot is taken again from the current dictionary, the same idempotent
  import as from search.
- Every part the origin has, in order, with its `origin`, `enabled` flag and text:
  - **imported parts** only to be located: by their place among the imported parts
    of the same list (imported senses keep no dictionary sense id), checked against
    their text where they have one (spellings, readings, meanings);
  - **added parts** (spellings, readings, senses, meanings, examples) to be copied,
    with their id (and `copied_from_id`, if they were copies) as provenance.
- Notes (entry, sense, kanji) and `is_active`.
- Words of the user's own have no reference: everything in them is `added`, so they
  travel whole.

Exercises, sessions and statistics are never part of it.

### How it's imported

- **Always into a new collection.** It keeps the name, with a suffix when the user
  already has one by that name ("N5 (2)"), and records
  `copied_from_collection_id`. It never merges into an existing collection.
- **Reuse what the user has.** A dictionary item already in the library is reused; a
  missing one is imported from the dictionary; one the dictionary no longer has is
  skipped and reported. A word of the user's own is reused when the user already has
  it (by provenance, below), and created otherwise.
- **What the import creates takes the origin's state; what the user had keeps
  theirs.**
  - Added parts the item doesn't have yet are appended, with their enabled flag.
  - Imported parts' enabled flags and `is_active` apply only to items this import
    created.
  - Notes are copied only where the user has none (entry, sense, kanji); otherwise the
    user's are kept.
  - An added meaning in another language than its sense's is skipped (a sense's
    meanings are in one language). So are the added meanings and examples of an
    imported sense that can't be located (the dictionary changed).
- **Nothing is duplicated.** Two parts are the same when their ids or `copied_from_id`
  overlap: re-importing a file, or importing back a copy of one's own collection, adds
  nothing twice. Ids are compared within the same item (parts) or among the user's own
  words (whole words), so a coincidence with ids from another database only skips a
  part, never mixes users' data.
- What is copied is decided by aggregate methods (`PracticeEntry` / `PracticeKanji`),
  not route logic. The whole import is one transaction: an invalid file imports
  nothing.

### Provenance

- `copied_from_collection_id` on the collection, to download it again or update it.
- `copied_from_id` on every copied element (spelling, reading, sense, meaning, example,
  word of the user's own): the origin element's id, while the copy gets its own. It's
  what keeps re-imports from duplicating, lets a later "update" be offered when the
  origin changed, and lets what came from it be filtered or disabled.
- No foreign key: the origin may belong to another user, or another database, and may
  disappear. It points to the immediate origin, not the whole chain.

### Rejected

- A separate copy of the collection with its own entries: it duplicates on purpose,
  confuses when the same word has different data, and clashes with
  `(user_id, source_entry_id)`.
- A full snapshot in the file: the import would ignore most of it (the dictionary is
  the source of its data), and #82 would need a second format.

### Public collections (#82, future)

- The owner marks a collection public; that is the permission. Importing downloads a
  copy once and never syncs with the origin. The payload is read from the database
  instead of a file; the rest is the above.
- **Later:** pick what to import in a preview with toggles before applying, like
  enabling and disabling parts for the exercises.

## Order

Own senses first, then own examples and own entries (independent of each other), then
exporting and importing files (#86), and shared collections last: they need `origin`
on every part and reuse #86's import.
