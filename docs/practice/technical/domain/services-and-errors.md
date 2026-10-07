# Domain Services, Errors and Clock

[← Technical documentation](../README.md)

Pure business rules that don't belong to a single entity, the domain exceptions, and
the domain's notion of "now".

## Services (`domain/services/`)

### `collection_service.ensure_combinable(collections)`

Checks that collections can be merged into one pool (e.g. for an exercise):

- all have the same owner, else `CollectionOwnershipError`;
- all are the same subclass (all `EntryCollection` or all `KanjiCollection`), else
  `CollectionKindMismatchError`.

An empty list is combinable. The union of their members is computed by the
repository (`item_ids`), not here.

### `study_field_service`: reading what an exercise studies

`entry_card(entry, fields, meaning_lang)` / `kanji_card(kanji, fields, meaning_lang)`
build a `StudyCard`: the item's id and, for each field, its enabled values as
`FieldValue(text, keys)`. `meaning_lang` is the language as the items store it (`eng`
for glosses, `en` for kanji meanings). Keys are what values are compared by:
`kana_key` (katakana as hiragana, no `.` or `-`) and `gloss_key` (lower-case, no
"to ", no parentheses), one key per gloss of a meaning. `StudyCard.answers(field)`
is what can be asked or offered: only the first value of a word's `writing` and
`reading` (`first_only`), every value otherwise. Details:
[exercises](../exercises.md#reading-a-field-from-an-item).
`kanji_literal(card)` is a kanji card's kanji (`None` for a word).

`entry_label(entry)` names a word outside a card (in statistics): `(label, reading)`,
its usual form as asked (`entry_card`'s first enabled spelling, else its first
enabled reading) plus its reading when the label is a spelling. With every spelling
and reading disabled, it falls back to the dictionary's first spelling or reading.

### `question_order_service`

What every card exercise type shares:

- `items_in_order(eligible, history, rng)`: the items in the order to try them. Missed
  items due for review come first (after `REVIEW_GAP` questions, never two reviews in
  a row), then the deck (each item once per round), then any other; never the last
  one again ([details](../exercises.md#which-item-comes-next)).
- `eligible_items(cards, settings)` lists the items some direction can ask
  (`can_ask`); `ensure_enough_items` raises `ExercisePoolTooSmallError` with fewer
  than `MIN_POOL_SIZE` (2).
- `fits_prompt(other, card, prompt)`: whether another item answers the same prompt
  (the basis of [the distractor rule](../exercises.md#the-rule)).
- `card_front(card, direction)` and `card_back(card, direction, settings)`: what the
  card shows before and after answering.

### `choice_question_service.build_next_question(cards, settings, history, rng)`

Builds a session's next choice-card question from the pool's cards and the session's
history, with the injected `random.Random`: the first of the `items_in_order` that can be
asked. Directions are tried in random order, and distractors are picked so that
**none is a valid answer** ([the rule](../exercises.md#the-rule)). Raises
`ExercisePoolTooSmallError` if the pool is too small or no question can be built.

### `handwriting_question_service.draft_next_question(cards, settings, history, drawable, rng)`

Picks the next handwriting question's item and direction among the kanji in
`drawable` (those with a stroke order), as a `HandwritingDraft`: prompt, back and the
accepted kanji (every pool kanji that fits the prompt, the asked one first).
`draft.question(position, references)` turns it into the `HandwritingQuestion` once
the caller has their strokes (`references` by literal): accepted kanji without
strokes are left out, and the asked one must have them (`ExercisePoolTooSmallError`
otherwise). `ensure_enough_drawable_items` raises
`ExercisePoolTooSmallError` with fewer than 2 drawable kanji. See
[exercises](../exercises.md#questions).

### `stroke_geometry_service`

Pure geometry on strokes (tuples of points): `normalize` (centred on the bounding box,
scaled by its longer side), `resample(stroke, n)` (evenly spaced points),
`mean_distance` (pairwise, so direction counts) and `chamfer` (as pictures, ignoring
order). SVG paths are never parsed here: reference strokes arrive as points.

### `handwriting_grading_service.grade_drawing(drawing, references)`

Grades a `StrokesAnswer` against each accepted `ReferenceKanji` and returns the
closest `HandwritingGrade` (score, verdict, matched kanji, a status per stroke).
`ValueError` with no references. Algorithm and thresholds:
[exercises](../exercises.md#grading).

### `word_handwriting_question_service.draft_next_word_question(...)`

The next word to write: like `draft_next_question`, among the words whose every
character has a stroke order and that fit `MAX_CELLS`; it accepts every word of the
pool that fits the prompt and is as long. `word_characters` lists the characters to
ask the dictionary about; `ensure_enough_writable_items` checks the pool. The draft's
`question(position, references)` builds the `WordHandwritingQuestion`.

### `handwriting_grading_service.grade_kana(drawing, expected, alphabet)`

A kana's grade, also against every kana of `alphabet`: another that fits clearly
better makes it `wrong` with `looks_like`; otherwise a recognisable kana is at worst
`close`.

### `word_grading_service.grade_word(answer, words, alphabet)`

Grades a `CellsAnswer` cell by cell (an empty cell: every stroke `missing`; a kana
with `grade_kana` when `alphabet`, the kana's references, is given; small kana by
size against the word's other kana) against each accepted word as long as it, and
returns the closest `WordGrade`: the worst cell's verdict, the cells' average score.
`KANA`, `TWINS` and `SMALL_TWINS` list the kana and their small / big twins.
[exercises](../exercises.md#words).

## Exceptions (`domain/exceptions.py`)

| Exception | Base | Raised when |
|---|---|---|
| `CollectionOwnershipError` | `ValueError` | Collections of different users are combined, or an item is added to another user's collection |
| `CollectionKindMismatchError` | `ValueError` | Entry and kanji collections are combined |
| `EntityNotFoundError` | `LookupError` | An update/delete targets something that doesn't exist or belongs to another user |
| `CollectionNameTakenError` | `ValueError` | A collection is added or renamed to a name the user already has for that kind (HTTP `409`) |
| `OriginalDataError` | `ValueError` | An imported (dictionary) meaning is edited or removed; it can only be disabled (HTTP `409`) |
| `DictionaryItemNotFoundError` | `LookupError` | An import asks for an entry or kanji the dictionary doesn't have (HTTP `404`) |
| `ExercisePoolTooSmallError` | `ValueError` | An exercise's collections don't have enough usable items for a session (HTTP `422`) |
| `QuestionNotActiveError` | `ValueError` | An answer to a question that isn't the session's active one, or a question asked while another is active (HTTP `409`) |
| `SessionAlreadyOpenError` | `ValueError` | A session is stored while the user has another open one; a user studies one at a time (HTTP `409`) |
| `SessionFinishedError` | `ValueError` | An answer or question on a finished (or idle) session (HTTP `409`) |
| `InvalidAnswerError` | `ValueError` | An answer doesn't fit its question, e.g. an option it doesn't have (HTTP `422`) |

## Clock (`domain/clock.py`)

`utc_now()` returns `datetime.now(UTC)`, an aware UTC datetime. It's the only source
of "now" for entities and repositories. See
[dates and time zones](../cross-cutting/dates-and-time-zones.md).
