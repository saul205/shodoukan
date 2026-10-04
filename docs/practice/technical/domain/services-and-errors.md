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

### `choice_question_service.build_choice_questions(cards, settings, rng)`

Builds a choice-card session's questions from the pool's cards with the injected
`random.Random`: shuffles the eligible items, takes `question_count` (or all), tries
each item's directions in random order, and picks distractors so that **none is a
valid answer** (the [rule](../exercises.md#the-rule)). An item no direction can ask
about without an ambiguous option is skipped. Raises `ExercisePoolTooSmallError` if
fewer than `MIN_POOL_SIZE` (2) items can be asked about, or no question can be built.

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
| `QuestionAnsweredError` | `ValueError` | A session question is answered a second time (HTTP `409`) |
| `InvalidAnswerError` | `ValueError` | An answer doesn't fit its question, e.g. an option it doesn't have (HTTP `422`) |

## Clock (`domain/clock.py`)

`utc_now()` returns `datetime.now(UTC)`, an aware UTC datetime. It's the only source
of "now" for entities and repositories. See
[dates and time zones](../cross-cutting/dates-and-time-zones.md).
