# Exercises — Design

[← Technical documentation](README.md)

The design of interactive exercises: how they're defined, run, graded and kept for
statistics, and how new exercise types fit in. Parts that are built are marked
**(built)**; the rest is the agreed design for the phases listed at the end. When a
phase lands, its details move to the layer pages (entities, schema, endpoints, use
cases) and this page keeps the overview.

What the user sees: [functional documentation](../functional/exercises/README.md).

## Concepts

| Concept | What it is | Lifetime |
|---|---|---|
| `Exercise` | A saved definition: which collections, which exercise type, and its settings. | Created, edited and deleted by the user |
| `ExerciseSession` | One study session of an exercise: its active question and the questions answered so far. | Started when the user launches the exercise; open-ended, until finished or idle |
| Statistics | Read-only queries over sessions and their answers. | Derived, nothing stored twice |

**Sessions are the statistics module.** Every question keeps a snapshot of what was
shown and what the user answered, so reviewing a past session and computing accuracy
(per exercise, per item, per direction) are queries over the same rows. There is no
second store to keep in sync.

## Exercise types

An exercise has an **archetype** (the shape of the interaction) and a **type** within
it. `settings` is a discriminated union keyed by `type`, so a new type is a new member
of the union plus its question builder and its frontend component; nothing else
changes.

| `type` | Archetype | What the user does | Status |
|---|---|---|---|
| `card.choice` | Card | Sees the front, picks the right answer among N options | Phase 1–5 |
| `card.flip` | Card | Sees the front, flips the card, says whether they knew it | Future |
| `card.typed` | Card | Types the answer (kana, meaning) | Future |
| `card.handwriting` | Card | Draws the kanji; stroke data is checked or self-graded | Future |
| `sentence.gap` | Sentence | Fills the gaps of an example sentence with kanji, given the kana | Future |

All card types share `CardSettings`:

- `directions`: what the front shows and what is asked (see below).
- `back_fields`: what the back of the card shows once answered, besides the prompt and
  the answer.

`ChoiceCardSettings` (`type = "card.choice"`) adds:

| Setting | Values | Default |
|---|---|---|
| `option_count` | 2–8 | 4 |
| `distractor_source` | `"collection"` (later `"library"`) | `"collection"` |

## Sessions (built)

A session is open-ended: it lasts as long as the user keeps studying.

```
ExerciseSession
├─ exercise_id, exercise_name, item_kind, meaning_lang
├─ created_at (start) · updated_at (last activity) · finished_at
├─ current: ExerciseQuestion | None   ← the active question, not answered yet
└─ history: [ExerciseQuestion]         ← the answered ones, in order
```

1. **Launch** the exercise: a session starts with its first active question. The
   user's open session, of any exercise, is finished at its last activity: **a user
   studies one session at a time** (a partial unique index on open sessions per
   user enforces it).
2. **Answer** the active question: it's graded, moves to the history, and the next
   active question is built and returned with the grade.
3. **Finish**: the session is closed and its active question, never answered, is
   dropped, so it doesn't count in statistics.

There's never more than one active question, and it's stored: reloading the page
shows the same one, and the answer is graded against the options really shown.
An answer names the active question's id, so a double click or a stale tab can't
answer the next one by mistake.

### Which item comes next

Worked out from the history alone, with the current pool (items added or
deactivated mid-session count from the next question):

1. **Missed items come back**: an item whose last answer was wrong is asked again
   once `REVIEW_GAP` (3) questions went by, oldest miss first. Two reviews never come
   in a row, so a lot of misses can't stop the deck.
2. **The deck**: every item of the pool once per round, in random order; a round ends
   when every item was asked in it, and the next one is shuffled again.
3. **Fallback**: any other item, if the ones above can't make a question without an
   ambiguous option.

The same item is never asked twice in a row.

### Closing

The client finishes the session when the user leaves it (a Finish button, leaving the
page, a `fetch` with `keepalive` when the tab closes). As that can fail, a session also
ends:

- when the user starts another session, of any exercise;
- when it's been idle for `IDLE_TIMEOUT` (30 minutes): it counts as finished at its
  last activity, and answering it is refused (`409`);
- when its exercise is deleted: the answer that found out still counts.

**Open means `finished_at` is NULL _and_ the last activity is under 30 minutes old.**
An idle session isn't written when it's read or answered (`ended_at(now)` reports it
as finished); it's stored as finished, at its last activity, when the user finishes
it or starts the exercise again. A session nobody comes back to keeps a NULL
`finished_at` forever, so history and statistics apply the same rule.

## Fields and directions

The fields that can be studied depend on what the exercise holds:

| Item kind | Field | Example |
|---|---|---|
| Entries (words) | `writing` | 食べる |
| | `reading` | たべる |
| | `meaning` | to eat |
| Kanji | `literal` | 食 |
| | `onyomi` | ショク, ジキ |
| | `kunyomi` | た.べる, く.う |
| | `meaning` | eat, food |

A **direction** is `prompt → answer`: `prompt` is a non-empty list of fields shown on
the front, `answer` is the one field asked. `answer` can't be in `prompt`, and an
exercise can't repeat a direction. Each question picks one of the exercise's
directions at random.

The fields studied are the union of every direction. A field that is never in a
`prompt` is never shown on the front. Example: with *kunyomi → literal* and
*literal → onyomi*, kanji, on'yomi and kun'yomi are studied, but the front shows only
the kanji or its kun'yomi, never an on'yomi.

### Reading a field from an item

- Only **active** items and **enabled** parts count (readings, spellings, glosses and
  kanji meanings the user disabled are ignored).
- `meaning` uses the session's `meaning_lang`, chosen when the session starts (the
  sidebar language, as `useMeaningLang` in the frontend):
  - entry: the glosses of the first sense with glosses in that language, joined with
    "; ";
  - kanji: its meanings in that language, joined with ", ".
- A field can have several values (two kun'yomi, two spellings). Every value is
  compared (see below) and shown on the **back**.
  - **Kanji readings:** each is worth learning, so the asked value is picked at
    random among the enabled ones, and the front shows all of them.
  - **A word's spellings and readings:** the others are variants of the usual form
    (ヤマ for やま, がわ for かわ, 聴く for 聞く), so only the **first enabled** one is
    asked, offered as an option and shown on the front. The dictionary lists the usual
    form first; disabling it in the library makes the next one the asked form.
- An item that has no value for a field (a kana-only word has no `writing`, a kanji
  with no kun'yomi) isn't used for directions that need that field.

## Distractors: a wrong option must never be right

The options of a `card.choice` question are one correct answer plus distractors taken
from other items of the pool (the exercise's collections). A distractor must not also
be a valid answer to the prompt. Readings, meanings and spellings are shared often
(many kanji share an on'yomi, homophones share a reading), so this is checked
explicitly.

### Comparison keys

Values are compared one by one through a normalized key:

| Field | Key |
|---|---|
| Kana (`reading`, `onyomi`, `kunyomi`) | Katakana converted to hiragana; okurigana dots (`.`) and affix dashes (`-`) removed. ショク ≡ しょく, た.べる ≡ たべる |
| `meaning` | Each gloss on its own: lowercase, a leading "to " removed, text in parentheses removed, whitespace collapsed. Two meanings match if they share a gloss |
| `writing`, `literal` | The text as is |

### The rule

A question shows the prompt values of the correct item **C** and asks for field
**A**. A candidate option text **t** (the value of A of some item **D**) is
**rejected** if there is any item **X** in the pool, C included, such that:

1. **X fits the prompt**: for every prompt field, X shares at least one key with C;
   and
2. **t matches one of X's values for A** (by key).

That covers:

- **D fits the prompt, so its answer is also right.** *reading → writing* for 箸
  (はし): 橋 is also はし, so 橋 can't be a wrong option. *kunyomi → literal*: two
  kanji with the kun'yomi はし. *literal → meaning* has no such case, but
  *onyomi → literal* does: 校 and 高 are both コウ.
- **t repeats a valid answer of C.** *meaning → reading* for 箸: a distractor whose
  reading is はし (from 橋) would look wrong but is C's own reading.
- **t equals the answer of a third item that fits the prompt.** *meaning → reading*
  for 話す ("to speak"): 言う (いう) also means "to speak", so いう is a valid answer.
  A distractor いう coming from 云う ("to say", which doesn't fit) is rejected too.

Further rules:

- Option texts are distinct by key.
- If fewer distractors than `option_count − 1` survive, the question has fewer options
  (at least 2). If none survive, the item is tried with another direction, and skipped
  if no direction works.
- A pool with fewer than 2 eligible items can't start a session
  (`ExercisePoolTooSmallError`, HTTP `422`).

### Where it lives

Pure domain services, testable with a seeded `random.Random`:

- `domain/services/study_field_service.py`: reads a field's values from a
  `PracticeEntry` / `PracticeKanji`, and builds their comparison keys. Katakana to
  hiragana is a code-point shift, so the domain doesn't need the `KanaGateway`.
- `domain/services/choice_question_service.py`: `build_next_question` picks the next
  item (see [which item comes next](#which-item-comes-next)) and direction, the
  answer value and the distractors, applying the rule above.

Tests cover every ambiguity: shared kun'yomi, shared on'yomi, homophones, synonyms,
same spelling.

## Storage

### Exercise definitions (built)

| Table | Columns |
|---|---|
| `exercises` | `id`, `user_id` → `users` (cascade), `name` (1–100), `description`, `item_kind` (`entries` / `kanji`, check constraint), `settings` (JSON), `created_at`, `updated_at` |
| `exercise_entry_collections` | `exercise_id` → `exercises`, `collection_id` → `entry_collections`; both cascade |
| `exercise_kanji_collections` | `exercise_id` → `exercises`, `collection_id` → `kanji_collections`; both cascade |

`settings` is JSON validated by the domain model on the way in and out: it is always
read and written whole and never queried by its parts (unlike the item snapshot, which
is normalized so single parts can be toggled). Deleting a collection removes it from
every exercise; an exercise left with no collections stays, but can't start a session
until it gets one.

### Sessions and answers (built)

| Table | Columns |
|---|---|
| `exercise_sessions` | `id`, `user_id`, `exercise_id` (→ `exercises`, `SET NULL` on delete, so history survives), `exercise_name` (snapshot), `item_kind`, `meaning_lang`, `created_at` (the start), `updated_at`, `finished_at` |
| `exercise_questions` | `id`, `session_id` (cascade), `position`, `entry_id` / `kanji_id` (one of them, by the session's kind; `SET NULL` when the item leaves the library), `prompt_fields`, `answer_field`, `prompt` / `options` / `back` (JSON snapshot), `correct_option`, `answer` (JSON, SQL `NULL` until answered), `is_correct`, `answered_at`, `response_ms` |

The active question and the history share `exercise_questions`: the active one is the
row with no answer. Finishing a session deletes that row.

Each option keeps the id of the item it came from, for opening its detail from the
review; that id isn't updated if the item is later removed.

The queryable columns (`item_id`, `answer_field`, `is_correct`, `answered_at`, ...) are
what statistics filter and group by. `answer` is a discriminated union like
`settings`: `{type: "option", option}` now; later `{type: "text", text}`,
`{type: "self_grade", knew}` and `{type: "strokes", strokes}`.

The snapshot keeps a past session readable exactly as it was, even after the item is
edited or deleted.

## API

### Exercise definitions (built)

| Method | Route | Body / result |
|---|---|---|
| `GET` | `/exercises` | The user's exercises, sorted by name |
| `POST` | `/exercises` | `ExerciseRequest` → `201` `ExerciseResponse` |
| `GET` | `/exercises/{id}` | `ExerciseResponse` |
| `PUT` | `/exercises/{id}` | `ExerciseRequest` (whole replacement; `item_kind` can't change) |
| `DELETE` | `/exercises/{id}` | `204` |

Details: [endpoints](api/endpoints.md#exercises).

### Sessions (built)

| Method | Route | Body / result |
|---|---|---|
| `POST` | `/exercises/{id}/sessions` | `{meaning_lang}` → the session with its first active question, **without** the solution (item, correct option, back) |
| `POST` | `/exercise-sessions/{id}/answer` | `{question_id, answer: {type: "option", option}, response_ms}` → the graded question with its solution, the `next` active question, the counts |
| `GET` | `/exercise-sessions/{id}` | The session: its active question (without solution) and its history (with) |
| `POST` | `/exercise-sessions/{id}/finish` | Close it; idempotent |
| `GET` | `/exercises/{id}/sessions` | History, one row per session with its score (phase 5) |

Details: [endpoints](api/endpoints.md#exercise-sessions).

The server generates the questions and grades the answers, so statistics don't depend
on the client and library-wide distractors (later) need no paging in the browser.

## Frontend (phases 3–5)

In `shodoukan-practice-web`:

- **Pages:** `exercises/index.vue` (list, start, edit), `exercises/new.vue` and
  `exercises/[id]/edit.vue`, `exercises/[id]/index.vue` (summary and history),
  `exercise-sessions/[id].vue` (play, then review).
- **Components:**
  - `ExerciseForm` with a `DirectionsEditor` (rows of prompt fields → answer field)
    and back-field checkboxes; the field list depends on the item kind.
  - `StudyCard`: front and back of a card. The back shows the prompt, the answer and
    the chosen `back_fields`.
  - `ChoiceOptions`: the options; once answered, the picked one is red if wrong, the
    correct one green.
  - `ItemDetailModal`: opens the item's full detail without leaving the session. It
    reuses `EntryDetail` / `KanjiDetail`, extracted from
    `app/pages/library/entries/[id].vue` and `app/pages/library/kanji/[id].vue`.
- A registry `type → component` picks the player for each exercise type.
- "Ejercicios" in the sidebar (`app/layouts/default.vue`).

Example of a `card.choice` question, direction *literal → kunyomi*:

```
Front: 食                        Back: 食 · たべる · eat, food
Options:                         Options:
  あるく                            あるく   ← picked (red)
  みち                              みち
  たべる                            たべる   ← correct (green)
  すこし                            すこし
```

## Phases

Branches: `saul205/27_add-the-interactive-exercises-to-the-practice-app` is the
umbrella. The choice card (#28) is `saul205/28_select-between-x-options-exercise`:
phase 1 was built on it, and each later phase is a branch off it
(`saul205/<issue>_<description>`) that merges back with a PR.

| # | Phase | Scope |
|---|---|---|
| 1 | Exercise definitions (backend) **(built)** | Entity, settings union, storage, CRUD use cases and routes |
| 2 | Exercise sessions (backend) **(built)** | Field reading and comparison keys, question builder with the distractor rule, sessions and answers storage, session routes |
| 3 | Exercise list and creation (frontend) | Exercises pages, `ExerciseForm`, `DirectionsEditor`, one collection |
| 4 | Playing a choice session (frontend) | `StudyCard`, `ChoiceOptions`, back of the card, `ItemDetailModal` (extract `EntryDetail` / `KanjiDetail`) |
| 5 | History and review (statistics) | Session history per exercise, reviewing a past session, accuracy per item |
| 6 | Several collections and library distractors | Pick several collections in the form (the backend already accepts them), `distractor_source = "library"` |
| — | Future types | `card.flip`, `card.typed`, `card.handwriting`, `sentence.gap` |
