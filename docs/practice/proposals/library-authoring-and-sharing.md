# Proposal: own library content and shared collections

> **Status: proposal, not implemented** (agreed 2026-10-08). As each part is built, it
> moves to the real docs ([entities](../technical/domain/entities.md),
> [decisions](../technical/decisions.md), [customise](../functional/library/customise.md))
> and leaves this page, which ends up holding only shared collections.

Issues: #79 own senses (parent), #80 own example sentences and #81 entries from scratch
(both branch from #79, independent of each other), #82 import public collections
(future).

## Own senses (#79)

Today glosses can be added to imported senses, but senses can't be created, nor
enabled or disabled (`EntryPart` has no `senses`).

- `PracticeSense` gets `origin` (`imported` / `added`) and `enabled`; `"senses"` joins
  `EntryPart`.
- Own senses can be added to imported and own entries. They hold glosses, examples and
  notes; `pos` / `misc` stay empty for now (later, picked from JMDict's codes).
- Only own senses are edited and removed (with their glosses and examples). Imported
  senses are only disabled, like the rest of the dictionary data. Both still take new
  glosses and examples.
- Disabling a sense keeps its glosses' and examples' own flags, so re-enabling restores
  it as it was. A gloss shows when `sense.enabled and gloss.enabled`: applied in the
  views, the library search and the exercise questions.

## Own example sentences (#80)

- Same shape as the imported ones: linked to a sense, which the user picks or creates.
  Japanese text plus one or more translations (`PracticeExampleSentence`).
- `PracticeExample.origin` already exists. Add `add_example` / `edit_example` /
  `remove_example` following the own-gloss pattern (`_own_gloss`), one endpoint each.

## Entries from scratch (#81)

For groups JMDict doesn't have, such as counters with their numbers (三匹).

- `source_entry_id: int | None`. Whether an entry is the user's own is derived from
  `None` (a property, no stored flag that could disagree with it). The
  `(user_id, source_entry_id)` unique constraint still holds: NULLs are distinct in
  PostgreSQL.
- `origin` on every part: `PracticeReading` and `PracticeKanjiReading` get it too.
  Everything in an own entry is `added`; imported data behaves as before.
- Own entries can be deleted; imported ones are still deactivated.
- When the spelling matches a dictionary entry, offer to import it instead (a warning,
  not a block).
- Handwriting already works, since KanjiVG goes character by character. The choice
  questions' distractors need checking with entries that have no dictionary data.

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
