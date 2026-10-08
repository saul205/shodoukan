# Proposal: own library content and shared collections

> **Status: proposal, not implemented** (agreed 2026-10-08). As each part is built, it
> moves to the real docs ([entities](../technical/domain/entities.md),
> [decisions](../technical/decisions.md), [customise](../functional/library/customise.md))
> and leaves this page, which ends up holding only shared collections.

Issues: #79 own senses (parent), #80 own example sentences and #81 entries from scratch
(both branch from #79, independent of each other), #82 import public collections
(future).

## Own senses (#79)

Built: see [entities](../technical/domain/entities.md#customisation-rules) and
[decisions](../technical/decisions.md#own-senses-start-with-a-meaning-a-disabled-sense-keeps-its-parts-flags).

## Own example sentences (#80)

- Same shape as the imported ones: linked to a sense, which the user picks or creates.
  Japanese text plus one or more translations (`PracticeExampleSentence`).
- `PracticeExample.origin` already exists. Add `add_example` / `edit_example` /
  `remove_example` following the own-gloss pattern (`_own_gloss`), one endpoint each.

## Entries from scratch (#81)

Built: see [entities](../technical/domain/entities.md#snapshot-and-practice-state),
[decisions](../technical/decisions.md#words-of-the-users-own-have-no-source-readings-can-be-added)
and [creating words of your own](../functional/library/create.md).

## Importing public collections (#82, future)

- The owner marks a collection public; that is the permission. Importing downloads a
  copy once and never syncs with the origin.
- **References only:** the collection is composed from the items the user already has,
  and the missing ones are imported from the dictionary (the existing idempotent
  import). The origin's own entries have no source, so they're always copied.
- **With data (append, the user's responsibility):** the origin's `added` parts (senses,
  glosses, examples, readings) are appended to the user's copy of each item.
  - A separate copy of the collection with its own entries is ruled out: it duplicates
    on purpose, confuses when the same word has different data, and clashes with
    `(user_id, source_entry_id)`.
  - The origin's enabled flags don't apply to items the user already has.
  - Notes are copied when the user has none; otherwise they're kept, or appended with a
    separator (to decide).
- **Provenance on two levels:**
  - `copied_from_collection_id` on the collection, to download it again or update it.
  - `copied_from_id` on every copied element (sense, gloss, example, reading, own
    entry): the origin element's id, while the copy gets its own. Downloading again
    doesn't duplicate (more reliable than comparing text, which breaks when the owner
    edits it), a later "update" can be offered when the origin changed, and what came
    from it can be filtered or disabled.
  - No foreign key (or `ON DELETE SET NULL`): the origin belongs to another user and may
    disappear. It points to the immediate origin, not the whole chain.
- **Later:** pick what to import in a preview with toggles before applying, like
  enabling and disabling parts for the exercises.
- What is copied is decided by an aggregate method, not route logic. Exercises and
  their history aren't shared.

## Order

Own senses first, then own examples and own entries (independent of each other), and
shared collections last: they need `origin` on every part.
