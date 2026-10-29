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

### `collection_service.free_collection_name(name, taken)`

The name an imported collection gets: `name` (stripped, cut to 100 characters), or
with the first free suffix (`"N5 (2)"`, `"N5 (3)"`, ...) when it's in `taken`, cutting
the name so the suffix fits.

### `study_field_service`: reading what an exercise studies

`entry_card(text, fields)` / `kanji_card(text, fields)` build a `StudyCard` from an
item's study read model (`EntryStudyText` / `KanjiStudyText`, see
[repository ports](repository-ports.md)): the item's id and, for each field, its
enabled values as `FieldValue(text, keys)`; a word's meaning is its first sense's
glosses. `entry_study_text(entry, meaning_lang)` / `kanji_study_text(kanji,
meaning_lang)` turn a loaded aggregate into that read model, with the same rules the
repositories apply in SQL. `meaning_lang` is the language as the items store it
(`eng` for glosses, `en` for kanji meanings). Keys are what values are compared by:
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

### `inflection_service`: the form of a word in a sentence

A gap covers one or more `Morpheme`s: the word (its **head**, the first content
morpheme, after a prefix like お) and whatever inflects it (引か + れ + た).

- `is_content_word(m)`: its part of speech is in `CONTENT_POS` (nouns, pronouns,
  verbs, adjectives, adjectival nouns, adverbs, adnominals, interjections), not a
  particle, auxiliary, prefix or symbol.
- `gap_head(morphemes)`: the head, or `None`.
- `gap_inflection(morphemes)`: an `Inflection(endings, form)`, the lemmas of the
  morphemes after the word and the last one's form without its variant (終止形 for
  終止形-一般; `None` when it doesn't inflect). The word is the head with the content
  words and suffixes right after it (勉強 + し in 勉強した, 七 + つ in 七つ, which has
  no endings). 引かれた and 飲まれた are both `(れる, た) · 終止形`. What looks the same
  is merged: past だ is た, te-form で is て (the conjunctive particle only), られる is
  れる, させる is せる, and 連体形 is 終止形 (走った人 / 走った。) except for the copula
  (な / だ). Fill-the-gap options are other words with the same inflection.
- `gap_dictionary_forms(morphemes)`: how the word may be written in the dictionary,
  best first: the head's lemma (引く), the gap as written (共に, several morphemes),
  and the gap with its last morpheme as a lemma (いけない, an expression). Used to
  find the gap's word in the library.

### `sentence_analysis_service`: a sentence's words from its morphemes

- `span_morphemes(morphemes, start, end)`: the morphemes exactly covering a span, or
  `None` when it cuts one (心地 inside 使い心地).
- `analyze_gap(morphemes, forms=())` → `GapAnalysis(lemma, reading, pos,
  inflection)`: the lemma is the first of `gap_dictionary_forms` that is one of the
  linked word's `forms` (its enabled spellings and readings), else the head's lemma;
  the reading is the gap's in context, in hiragana (katakana for a word written in
  katakana); `pos` is the head's.
- `find_gap(morphemes, forms, taken=())`: where a linked word without a span is: the
  first content morpheme whose lemma is one of `forms` (kana compared as hiragana), or
  that starts an expression of up to four morphemes which is (持って + いっ for
  持っていく: as written, then the last one's lemma), with what inflects it
  (auxiliaries, te-form て / で), clear of the `taken` spans. A word written in kanji
  is found by its spelling, one in kana by its reading.

### `sentence_sharing_service`: a word's sentences in a collection

What [sentences in a collection](entities.md#sentences-in-a-collection) describes:

- `with_examples(shared, entry, sentences)`: the word's `to_shared()` with its
  sentences as examples, each under the sense its word is linked to (the first when
  none), with its gap and analysis (`SharedExample.word`).
- `merge_examples(entry, shared, candidates, *, created, source)` →
  `SentenceMerge(created, changed)`: dictionary sentences located by text among the
  candidates and linked (their flag taken only when `created`), copies of someone's
  own matched by version (linked, `brought_by(source)`) or created
  (`PracticeSentence.copied`, linked at the shared gap with its analysis when it fits,
  without a gap otherwise), dismissed ones skipped. New copies join `candidates`, so a
  sentence that comes twice is copied once.
- `prune_examples(sentences, shared, source)` → `(changed, removed)`: copies `source`
  brought, untouched, whose version the new snapshot lacks let go of it; those nothing
  brings any more are removed.
- `preview_sentences(shared, user_id)`: the word's examples as unstored sentences,
  each once, with their gap: what a preview shows.

## Exceptions (`domain/exceptions.py`)

| Exception | Base | Raised when |
|---|---|---|
| `CollectionOwnershipError` | `ValueError` | Collections of different users are combined, or an item is added to another user's collection |
| `CollectionKindMismatchError` | `ValueError` | Entry and kanji collections are combined |
| `EntityNotFoundError` | `LookupError` | An update/delete targets something that doesn't exist or belongs to another user |
| `CollectionNameTakenError` | `ValueError` | A collection is added or renamed to a name the user already has for that kind (HTTP `409`) |
| `OriginalDataError` | `ValueError` | An imported (dictionary) spelling, reading, sense or meaning is edited or removed; it can only be disabled (HTTP `409`) |
| `LastReadingError` | `ValueError` | A word's only reading is removed: a word keeps one (HTTP `409`) |
| `LastMeaningError` | `ValueError` | A sense's only meaning is removed: a sense keeps one; the own sense is removed instead (HTTP `409`) |
| `SenseLanguageError` | `ValueError` | A meaning in another language is added to a sense: a sense's meanings are in one language (HTTP `422`) |
| `DictionaryItemNotFoundError` | `LookupError` | An import asks for an entry or kanji the dictionary doesn't have (HTTP `404`) |
| `ExercisePoolTooSmallError` | `ValueError` | An exercise's collections don't have enough usable items for a session (HTTP `422`) |
| `QuestionNotActiveError` | `ValueError` | An answer to a question that isn't the session's active one, or a question asked while another is active (HTTP `409`) |
| `SessionAlreadyOpenError` | `ValueError` | A session is stored while the user has another open one; a user studies one at a time (HTTP `409`) |
| `SessionFinishedError` | `ValueError` | An answer or question on a finished (or idle) session (HTTP `409`) |
| `InvalidAnswerError` | `ValueError` | An answer doesn't fit its question, e.g. an option it doesn't have (HTTP `422`) |
| `SentenceWordError` | `ValueError` | A sentence's word that can't be: a span outside the sentence or over another word, an analysis of a word without a span, a lemma or reading that isn't one (HTTP `422`) |

## Clock (`domain/clock.py`)

`utc_now()` returns `datetime.now(UTC)`, an aware UTC datetime. It's the only source
of "now" for entities and repositories. See
[dates and time zones](../cross-cutting/dates-and-time-zones.md).
