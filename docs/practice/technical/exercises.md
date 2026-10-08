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
| `card.handwriting` | Card | Draws the kanji, or writes a word (its spelling or reading) a character per cell; the strokes are graded against KanjiVG | #37, #67 **(built)** |
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

`HandwritingCardSettings` (`type = "card.handwriting"`) adds nothing, but every
direction must ask for something to write (`HANDWRITING_ANSWERS`): `literal` in a
kanji exercise, `writing` or `reading` in an entry exercise (the item kind's fields
decide which).

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
- `domain/services/question_order_service.py`: which item comes next (see
  [which item comes next](#which-item-comes-next)), shared by every card type, and
  the card's front and back.
- `domain/services/choice_question_service.py`: `build_next_question` picks the
  direction, the answer value and the distractors for that item, applying the rule
  above.

Tests cover every ambiguity: shared kun'yomi, shared on'yomi, homophones, synonyms,
same spelling.

## Handwriting

A `card.handwriting` question shows the front and asks the user to draw the kanji
(`answer_field` is always `literal`). The drawing is sent as strokes, in the order
drawn, each a list of points (`StrokesAnswer`), and graded on the server against the
KanjiVG strokes of the kanji, as the dictionary draws its stroke order.

### Questions

`handwriting_question_service.draft_next_question` picks the item like every card type
(`question_order_service`), among the kanji that **have a stroke order**: the use case
asks the dictionary which literals do (`DictionaryGateway.literals_with_strokes`) and
passes them in, and a pool with fewer than 2 of them can't start a session
(`ExercisePoolTooSmallError`, `422`). KanjiVG covers every jōyō kanji.

**Any kanji that fits the prompt is right**, by the same test as the
[distractor rule](#the-rule): asked for the kanji read はし with 橋 and 箸 both in the
pool, either is right. The draft lists the accepted kanji (the asked one first); the
use case fetches their strokes (`DictionaryGateway.stroke_references`, with each
stroke's centre line as points, computed by the anti-corruption mapper from KanjiVG's
paths) and builds the `HandwritingQuestion`, which keeps them as its snapshot. The
drawing is graded against the closest. Nothing else changes: back fields, missed
items coming back, the deck.

### Words

In an entry exercise, a handwriting card asks to write a word: its first spelling
(`writing`, okurigana included: 食べる) or its first reading (`reading`, in kana),
the same values a choice card asks. The question is a `WordHandwritingQuestion`
(`card.handwriting_word`), answered with a `CellsAnswer`: one drawing per character,
in the same space as a kanji, in order. Writing the reading is how kana words (これ)
and kana practice fit in.

- **Which words.** `word_handwriting_question_service.draft_next_word_question`
  picks the item like any card, among the words whose **every character** has a
  stroke order (KanjiVG draws the kana too: all of hiragana and katakana) and that
  fit in `MAX_CELLS` (12). The use case asks the dictionary about every character
  the exercise's words could need (`word_characters`).
- **Any word that fits the prompt is right**, like kanji, if it has **as many
  characters**: the question shows how many cells to write in (`cell_count`, the
  only part of the solution shown before answering), so a word of another length
  can't be what was meant. Each accepted word is a `ReferenceWord(text,
  characters)`, a `ReferenceKanji` per character.
- **Grading** (`word_grading_service.grade_word`): each cell is graded on its own
  against its character; an empty cell is that character `missing` (score 0,
  `wrong`). The word's verdict is the worst cell's and its score the cells'
  average. The closest accepted word counts. The grade is a `WordGrade(score,
  verdict, matched, cells)`.
- **Only another character fails a word** (#71). A word with a character written as
  another one is another word (たべる with ろ for る), so it's `wrong`; a slip in the
  right character leaves it at worst `close`:
  - **Kana are recognised** (`grade_kana`): a kana cell is also graded against every
    other kana (the use case reads their strokes, `KANA`, only for words that have
    kana). One that fits clearly better (a better verdict, or `RECOGNITION_MARGIN`
    = 10 more points) makes the cell `wrong`, naming it in the grade's
    `looks_like`, even when the drawing passes for the expected kana (ろ passes for
    る). Kana drawn alike in both scripts (へ / ヘ, べ / ベ, ぺ / ペ) and the small or
    big twin aren't rivals. Otherwise a recognisable kana (likeness ≥
    `SHAPE_CLOSE`, no marks missing or added whole) is at worst `close`: a stroke
    too many or too few in the right kana is a slip, not another kana (the kanji
    rule of no count errors under 5 strokes doesn't apply).
  - **Small kana** (ゃ / や, っ / つ, ァ / ア...) are told apart by size, since grading
    normalizes each cell by its own box. A cell's size is compared with the word's
    other big kana (kanji are left out: drawn bigger, and some flat like 一), against
    the sizes their references predict, and its twin's (a small kana is about
    `SMALL_RATIO` = 0.78 of its big twin in KanjiVG). Closer to the twin's: `wrong`,
    `looks_like` the twin; within `SIZE_BAND` (5 %) of the split: `close`. With no
    other big kana in the word, only a size clearly the twin's (`ALONE_MARGIN`)
    counts.
- A close word counts and comes back as a review, as a close kanji does.

Why one more question type rather than kanji as one-character words:
[decisions](decisions.md#words-are-written-a-character-per-cell-in-their-own-question-type).

### The drawing space

Points are in KanjiVG's own space, a 109-unit square (`CANVAS_SIZE`), the space the
frontend's stroke components draw in. The canvas shows a margin of 6 around it
(`CANVAS_MARGIN`), and points must stay inside the square plus the margin. A drawing
has up to 40 strokes (`MAX_STROKES`) of up to 300 points (`MAX_STROKE_POINTS`); the
client simplifies each stroke before sending it. Stored as is in `answer`, the
drawing is a few kilobytes of JSON, and the review draws it again from it. There's no
image: vectors draw sharply at any size and are what grading needs.

### Grading

`handwriting_grading_service.grade_drawing(drawing, references)` compares the drawing
with the kanji the question accepts and keeps the closest. Only those whose stroke
count is within one of the drawing's are compared, since no other can be close; the
asked kanji always is, so there's always a grade (a reading prompt such as コウ can
accept dozens of kanji). The use case passes the grade to the session
([decisions](decisions.md#a-drawing-is-graded-by-a-service-and-recorded-by-the-session)).

1. **Normalize.** The drawing and the reference are each centred on their bounding
   box and scaled by its longer side (`stroke_geometry_service.normalize`), so where
   and how big it was drawn doesn't count. Distances are then in kanji sizes: 0.1 is
   a tenth of the kanji. Each stroke is resampled to 16 evenly spaced points.
2. **The picture.** A chamfer distance between every point of both, blind to strokes
   and order, turned into a 0 to 1 likeness (`1 - distance / SHAPE_SCALE`).
3. **The strokes.** The distance between two strokes is the mean of their point
   distance and their furthest-apart ends. Each drawn stroke is paired with the
   reference stroke it resembles most, closest pairs first, each used once, up to
   `STROKE_MATCH`; drawn backwards still pairs.
4. **The lengths.** Each paired stroke's share of the drawing's total length is
   compared with its reference stroke's share of the kanji's: proportions between
   strokes, not sizes. It's off when the shares differ by more than
   `LENGTH_TOLERANCE` times **and** by more than `LENGTH_MIN_SHARE_GAP` of the total
   (the gap keeps a short stroke's natural wobble from counting). Dots (reference
   strokes under `MIN_LENGTH_CHECKED`) aren't checked. This is what tells 未 from 末.
5. **Marks.** In characters of up to `MARK_MAX_STROKES` (6) strokes, where a dot or
   a dakuten changes the character (kana, 犬, 太, 心), reference strokes smaller than
   `MARK_EXTENT` (0.2 of the character: dakuten, handakuten, dots) say little by
   their shape, so they're left out of step 3 and pair afterwards, with the drawn
   strokes left over, by the distance between their centres (up to `MARK_MATCH`,
   0.2; further than `MARK_OK`, 0.1, is `imprecise`), length unchecked. Their
   direction only counts when it's turned more than `MARK_REVERSED_ANGLE` (120°)
   from the reference's (`reversed`): a dakuten drawn at another angle is fine. In
   denser kanji, short strokes are ordinary strokes: 18 of 曜's are under 0.2, and
   treating them as marks hid their direction and failed a drawing missing one. A circle (゜,
   a closed stroke) only pairs with a circle. A run of marks (゛'s two strokes) may
   be drawn in any order. A run with none of its marks drawn, or short strokes drawn
   where the character has no marks, make another character (は for ば, ぱ for ば, 大
   for 犬): never `close`. Missing or extra marks don't count against the stroke
   count rule below.
6. **A status per stroke**, the first that applies:

   | Status | Meaning |
   |---|---|
   | `out_of_order` | Outside the longest run of reference strokes in writing order, so swapping two strokes is one mistake, not a cascade |
   | `reversed` | Drawn backwards |
   | `too_long` / `too_short` | Its length is off for the rest of the kanji (step 4) |
   | `imprecise` | Paired, but further than `STROKE_OK` |
   | `ok` | None of the above |
   | `extra` | A drawn stroke with no pair |
   | `missing` | A reference stroke not drawn |

7. **The verdict**, lenient on purpose: nobody writes as exactly as KanjiVG draws, so
   `imprecise`, `too_long` and `too_short` strokes are **warnings only**: they never
   lower the verdict
   ([decisions](decisions.md#a-drawing-close-enough-counts-and-comes-back)). It
   depends on the picture, the stroke order and direction, and the stroke count:
   - `correct`: likeness ≥ `SHAPE_OK`, and no stroke out of order, backwards, extra or
     missing.
   - `close`: likeness ≥ `SHAPE_CLOSE`; at most one stroke extra or missing, and none
     for kanji under 5 strokes (三 without a stroke is 二); and mistakes (out of
     order, backwards, extra, missing) on at most half of the strokes
     (`MISTAKE_CLOSE_SHARE`). It counts as right but comes back as a review.
   - `wrong` otherwise.

   `score` (0 to 100) is the mean of the picture likeness and the strokes' likeness
   (each pair `1 - distance / STROKE_MATCH`, over the larger stroke count), so it
   still shows how precise the drawing was. It's shown to the user; the verdict
   doesn't depend on it.

| Constant | Value |
|---|---|
| `STROKE_SAMPLES` | 16 |
| `STROKE_OK` (warning) | 0.12 |
| `STROKE_MATCH` | 0.28 |
| `SHAPE_SCALE` | 0.2 |
| `SHAPE_OK` / `SHAPE_CLOSE` | 0.6 / 0.4 |
| `ALLOWED_COUNT_ERRORS` / `COUNT_TOLERANCE_FROM` | 1 / 5 strokes |
| `MISTAKE_CLOSE_SHARE` | ½ |
| `MARK_EXTENT` / `MARK_MATCH` / `MARK_OK` | 0.2 / 0.2 / 0.1 |
| `MARK_MAX_STROKES` / `MARK_REVERSED_ANGLE` | 6 strokes / 120° |
| `LENGTH_TOLERANCE` / `LENGTH_MIN_SHARE_GAP` / `MIN_LENGTH_CHECKED` (warning) | 1.35 / 0.045 / 0.1 |

**Calibration.** The values were tuned on the KanjiVG strokes of 24 kanji drawn with
noise (moved, resized to 70–110 %, each stroke up to 3–5 units off, points shaking by
1.5–2.5), with strokes moved further, and on pairs of similar kanji drawn one for the
other:

- **The right kanji drawn with noise** is `correct`; only a very sloppy 食 with a
  stroke backwards drops to `close`. Length noise reaches a ratio of 1.40 on 1 % of
  strokes, but never with a share gap over 0.04 (0 of 1,220 strokes), so warnings
  stay rare on good drawings.
- **One stroke moved by up to ~24 units** (a fifth of the square) still pairs, as
  `imprecise`, and the drawing is `correct` in almost every kanji; with every stroke up
  to 8 units off, 84 of 92 drawings are `correct`. A `STROKE_MATCH` of 0.30 would let
  右 drawn for 左 through as `close`, so it stops at 0.28.
- **A stroke backwards, two swapped or one missing** is `close`.
- **Near twins** that differ only in stroke lengths or positions (未 / 末, 土 / 士,
  天 / 夫, 田 / 由) are `correct`, with warnings on the strokes that differ. That's
  the accepted cost of not failing on precision.
- **One stroke more or less in a kanji of 5 strokes or more** (木 for 本, 王 for 玉,
  休 / 体, 問 for 間) is `close`, by design: it can't be told from forgetting a stroke.
- **Other kanji** (a different stroke count or shape) are `wrong`, and so is a
  drawing too deformed to look like the kanji.

**Kana and marks** (#71) were checked the same way on KanjiVG's kana: every kana
drawn with noise (points up to 6 units off) is recognised as itself (0 of 177
wrong); a dakuten drawn longer and off its place, or its two strokes swapped, stays
`correct`; へ for べ, ぱ for ば, ば for は, ろ for る, ね for れ, シ for ツ, ソ for ン and
大 / 犬 are `wrong`; a kana with a stroke missing or extra, or half a dakuten, is
`close`; a dakuten drawn the other way is `close` (`reversed`), turned 60–100°
still `correct`; 曜 or 識 with a short stroke backwards report it (`close`), and 曜
without a short stroke is `close`, as without a long one. KanjiVG's marks measure 0.10–0.11 (゛), 0.18 (゜) and 0.12–0.17 (kanji
dots); シ's dots (0.18–0.19) are marks, ツ's (0.21–0.23) and ふ's aren't.

The values should be checked against real drawings once people use it. A handwriting
recognition model could replace this later: everything sits behind `grade_drawing`.
`tests/shodoukan-practice/domain/test_handwriting_grading_service.py` keeps these
cases.

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
| `exercise_questions` | `id`, `session_id` (cascade), `position`, `type`, `entry_id` / `kanji_id` (one of them, by the session's kind; `SET NULL` when the item leaves the library), `prompt_fields`, `answer_field`, `prompt` / `back` (JSON snapshot), `details` (JSON: what only the type has), `answer` (JSON, SQL `NULL` until answered), `is_correct`, `answered_at`, `response_ms` |

The active question and the history share `exercise_questions`: the active one is the
row with no answer. Finishing a session deletes that row.

Each option keeps the id of the item it came from, for opening its detail from the
review; that id isn't updated if the item is later removed.

The queryable columns (`item_id`, `answer_field`, `is_correct`, `answered_at`, ...) are
what statistics filter and group by. `details` holds what only the
question's type has: `{options, correct_option}` for a choice card, `{references,
grade}` for a handwriting card, `{words, grade}` for a word
([decisions](decisions.md#questions-are-a-union-too-with-what-each-type-adds-in-one-json-column)).
`answer` is a discriminated union like `settings`: `{type: "option", option}`,
`{type: "strokes", strokes}`, `{type: "cells", cells}` (a word) and
`{type: "skip"}` (a miss) now; later
`{type: "text", text}` and `{type: "self_grade", knew}`.

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
| `POST` | `/exercise-sessions/{id}/answer` | `{question_id, answer: {type: "option", option}, {type: "strokes", strokes}, {type: "cells", cells} or {type: "skip"}, response_ms}` → the graded question with its solution, the `next` active question, the counts |
| `GET` | `/exercise-sessions/{id}` | The session: its active question (without solution) and its history (with) |
| `POST` | `/exercise-sessions/{id}/finish` | Close it; idempotent |

Details: [endpoints](api/endpoints.md#exercise-sessions).

### History and statistics (built, #42)

| Method | Route | Result |
|---|---|---|
| `GET` | `/exercise-sessions?exercise_id=&status=open\|finished&limit=&offset=` | Paged session summaries, newest first, without questions: exercise, start, last activity, effective `finished_at`, answered, score. `status=open&limit=1` is the session to resume ("Continuar") |
| `GET` | `/exercises/{id}/statistics` | The exercise's totals (sessions, answers, right, accuracy, mean response time), accuracy per direction, most missed items |
| `GET` | `/statistics?days=30&tz=Europe/Madrid` | The same over every exercise (most missed words and kanji apart), plus answers per day in the user's time zone and a summary per exercise |

- **Open** means `finished_at IS NULL` and active within `IDLE_TIMEOUT`, the rule of
  `ExerciseSession.ended_at` written in SQL, so a summary and a full session agree.
- Aggregates are SQL `GROUP BY`s over `exercise_questions` joined to
  `exercise_sessions` (sessions are the statistics; nothing is stored twice). The
  most missed items show the item's **current** label from the library; items that
  left it (`item_id` null) aren't listed.
- Answers per day are grouped in Python with `zoneinfo` over the `answered_at` of the
  window (at most 365 days), so SQLite and PostgreSQL agree and days follow the
  user's time zone.
- Each question in a response carries `type` (`"card.choice"`,
  `"card.handwriting"` or `"card.handwriting_word"`), so the frontend picks the
  player by type.

Details: [endpoints](api/endpoints.md#exercise-statistics), [use
cases](application/use-cases.md#queries-queriesexercise_statistics_queriespy) and
[repositories](infrastructure/repositories.md#exercise-statistics).

The server generates the questions and grades the answers, so statistics don't depend
on the client and library-wide distractors (later) need no paging in the browser.

## Frontend (phases 3–5 and statistics)

In `shodoukan-practice-web`:

- **Pages:**
  - `exercises/index.vue`: the list, with Empezar, Editar and Eliminar, and a
    "Continuar" notice when a session is open (also on the home page) **(built)**.
  - `exercises/new.vue` and `exercises/[id]/edit.vue` **(built)**.
  - `exercises/[id]/index.vue`: the exercise's summary and session history
    **(built)**, and its statistics **(built)**.
  - `exercise-sessions/[id].vue`: play an open session **(built)**; a finished one
    shows its result and the review **(built)** (each answered question as
    it was, filter "solo falladas").
  - `statistics/index.vue`: totals, activity of the last 30 days, a table per
    exercise, most missed words and kanji **(built)**.
- **Components:**
  - `ExerciseForm` with several collections of one kind, a `DirectionsEditor` (rows
    of prompt fields → answer field) and back-field checkboxes; the field list
    depends on the item kind (`utils/study-fields.ts`) **(built**, see
    [frontend](frontend.md#screens)**)**.
  - `StudyCard`: front, then (once answered) the back alone. The back shows the
    prompt as the headline, the answer, and the chosen `back_fields` smaller
    **(built)**.
  - `ChoiceOptions`: the options, keys 1–N; once answered, the picked one is red if
    wrong, the correct one green **(built)**.
  - `ItemDetailModal`: opens an item's full detail without leaving the session (the
    asked item or a wrong option's). It reuses view-only `EntryDetail` /
    `KanjiDetail`, extracted from `app/pages/library/entries/[id].vue` and
    `app/pages/library/kanji/[id].vue` **(built)**.
  - `StatTile`, `AccuracyBar`, `ActivityChart`: Nuxt UI and CSS, no chart library
    **(built)**.
- A registry `question type → player component` picks the player for each exercise
  type (`components/exercise-players/`) **(built**; details in
  [frontend](frontend.md#screens)**)**.
- "Ejercicios" and "Estadísticas" in the sidebar **(built)** (`app/layouts/default.vue`).

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
(`saul205/<issue>_<description>`) that merges back with a PR. The remaining phases
go in the order 3 → A → 4 → 5 → C.

| # | Phase | Scope |
|---|---|---|
| 1 | Exercise definitions (backend) **(built)** | Entity, settings union, storage, CRUD use cases and routes |
| 2 | Exercise sessions (backend) **(built)** | Field reading and comparison keys, question builder with the distractor rule, sessions and answers storage, session routes |
| 3 | Exercise list and creation (frontend), #31 **(built)** | Exercises pages, `ExerciseForm` with several collections, `DirectionsEditor` |
| A | History and statistics (backend), #42 **(built)** | Session summaries (history, the open session), statistics per exercise and overall, question `type` |
| 4 | Playing a choice session (frontend), #32 **(built)** | Start and resume, `StudyCard`, `ChoiceOptions`, back of the card, `ItemDetailModal` (extract `EntryDetail` / `KanjiDetail`) |
| 5 | History and review (frontend), #33 **(built)** | Session history per exercise, reviewing a past session |
| C | Statistics (frontend), #43 **(built)** | Statistics per exercise and the "Estadísticas" page |
| 6 | Library distractors, #34 | `distractor_source = "library"` |
| 7 | Handwriting (backend), #58 **(built)** | `card.handwriting`: KanjiVG references, grading, questions by type in storage |
| 8 | Handwriting (frontend), #59 **(built)** | Drawing pad, the handwriting player, reviewing drawings |
| 9 | Writing words, #67 **(built)** | `card.handwriting_word`: a word's spelling or reading written a character per cell, graded per cell; its player and review |
| — | Future types | `card.flip`, `card.typed`, `sentence.gap` |
