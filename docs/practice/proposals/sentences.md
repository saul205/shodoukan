# Proposal: sentences in the library and sentence exercises

> **Status: proposal, not implemented** (agreed 2026-10-28). As each phase is built, it
> moves to the real docs ([entities](../technical/domain/entities.md),
> [exercises](../technical/exercises.md), [decisions](../technical/decisions.md)) and
> leaves this page.

Issues, one per phase, branches chained in this order: #95 sentence analyzer, #96
sentences in the library, #97 sentences API, #98 sentences in the frontend, #99
sentence choice exercises on words. #100 (sentence exercises for kanji) comes after.

## Why

Exercises built on sentences: fill a gap by picking the word, or give the reading or
the meaning of a word highlighted in a sentence. Today sentences only exist as
examples nested in each entry (`PracticeSense.examples`), which falls short:

- there is about one sentence per word (1.1 on average), so a sentence gets learnt by
  heart;
- a sentence can't serve several words: 4,922 JMDict sentences are already copied
  into more than one entry;
- the user's own examples don't mark where the word is in the sentence.

Measured on the dictionary: 80–91 % of the words of each JLPT level have at least one
JMDict sentence; the form of the word in the sentence (`examples.text`) is found
literally in it in 100 % of the cases (32,310 of 32,310), and is inflected in 19 %
(違った, 引かれた).

## Decisions

- **Sentences are library items of their own**, linked both ways to the user's words.
  A section of the library shows them and adds them, one at a time or in bulk.
- **No sentence collections.** Exercises read sentences through the words, and
  sharing or exporting a vocabulary collection carries its sentences. If exercises
  over a hand-picked set of sentences are ever needed, a third collection subclass
  fits without reworking anything.
- **Exercises still ask about words** (later, kanji); the sentence is the context.
- **Out of scope:** grammar (particles, patterns, theory) is a module of its own, to
  be designed later with written and reviewed exercises rather than generated ones;
  generating a correct grammar question automatically can't be guaranteed. Nested
  collections are out of scope too.

## Model

```
PracticeSentence (aggregate, library item like PracticeEntry)
├─ text (Japanese), translations [{lang, text}]
├─ active, notes, origin ("imported" from JMDict, original_id = example id | "own")
└─ words: [SentenceWord]              ← the sentence's words; those with a span are gaps
     ├─ start?, end?, surface?        ← span in the sentence, no overlaps; no span =
     │                                  linked to the word but not asked yet
     ├─ lemma, reading                ← editable (the analyzer gets 今日, 方 wrong)
     ├─ pos, inflection               ← part of speech and form signature
     │                                  (引かれた → れる + た·終止形)
     └─ entry_id?, sense_id?          ← link to the library word and sense
```

- **A linked word and a gap are the same thing:** a `SentenceWord` is the sentence's
  link to the vocabulary, and its span is what makes it askable as a gap.
- **Both ways, nothing duplicated.** The link lives in the `SentenceWord`; "the
  sentences of a word" is a reverse query on `entry_id`, and the entry page shows it
  instead of its examples.
- A JMDict sentence linked to two words is **one** `PracticeSentence` with two linked
  words, deduplicated by `original_id` on import.
- **Deactivating** a sentence takes it out of everything; unlinking a word takes it out
  of that word only. **Deleting a word** leaves its gaps unlinked: still askable for
  the reading, no longer for the meaning.
- **Sharing and export** of a vocabulary collection carry the active sentences linked
  to its words, replacing examples. Links to words outside the collection travel as
  dictionary ids and are relinked on import when the receiver has the word.
- A bulk-added sentence with no linked word is kept, and shown as "unlinked".
- **Kanji → sentences needs no stored link:** library words with an enabled writing
  containing the literal, their sentences, keeping the linked words whose surface
  contains the literal (drops sentences that spell the word in kana).

## Sentence analyzer (#95)

Built: the `MorphologyGateway` port
([repository ports](../technical/domain/repository-ports.md#morphologygateway)), its
SudachiPy adapter ([morphology gateway](../technical/infrastructure/morphology-gateway.md),
with the benchmark's figures), the form of a gap
([`inflection_service`](../technical/domain/services-and-errors.md#inflection_service-the-form-of-a-word-in-a-sentence))
and the
[decision](../technical/decisions.md#sentences-are-analyzed-with-sudachipy-and-only-gaps-are-stored).
A gap that isn't on morpheme boundaries (心地 in 使い心地) is analyzed on its own.

## Adding sentences

- **One sentence** (from the sentences section or from an entry): it's analyzed;
  content words one of whose dictionary forms (`gap_dictionary_forms`) matches an enabled writing or reading of the library are
  proposed. Kanji matches come marked as gaps, kana-only ones unmarked (はし is
  ambiguous). Particles and auxiliaries aren't proposed. The user confirms and picks
  the sense. From an entry, its gap comes already linked.
- **Bulk add:** paste many sentences, one per line, with an optional tab-separated
  translation. Before anything is stored, a summary to skim: one row per sentence
  with the detected words highlighted (kanji matches marked, kana-only ones in another
  colour), counts of linked, doubtful and unlinked words, a warning when there are
  none. "Save all", or open a row in the full editor (spans, links, sense, reading)
  and come back. The server analyzes all of them in one request.
- **Importing a word** imports its JMDict sentences as `PracticeSentence`s with the
  gap already linked (`examples.text` gives the span), so the entry page keeps showing
  what it shows today.

## Converting the existing examples (#96)

A full conversion, because the self-hosted pre holds many examples of the user's own.
On an empty database the conversion goes through zero rows and only the schema change
applies. It's written in self-contained SQL (no domain imports), since it stays in the
migration history while the domain keeps changing. Back up pre first and try the
migration on a restored copy.

Each `PracticeExample` becomes a `PracticeSentence` with one `SentenceWord` linked to
its entry and sense, keeping its active state, translations and version fields
(origin, original_id, source_id, edited_id, revision, source_collection_ids); the
dismissed references used by updating from the source (#90) point at the sentence.

1. **The Alembic migration** only does what text can:
   - JMDict examples: the span is the first occurrence of `examples.text` (237
     sentences contain it more than once; the user can fix those).
   - Own examples (empty `text`): the first enabled writing, then reading, found
     literally. Otherwise the word stays linked without a span: the sentence still
     shows on the entry page, and isn't asked until marked.
   - `lemma`, `reading`, `pos` and `inflection` stay empty.
   - Sentences shared by two words aren't merged: today each copy has its own state,
     and 17 pairs have overlapping spans (日本 / 日本語). Deduplication only applies to
     new imports.
2. **`shodoukan-practice analyze-sentences`**, run once after deploying and safe to
   run again: fills lemma, reading, pos and inflection; finds a span for linked words
   without one by matching the lemma (inflected own sentences);
   `--suggest-links` proposes links to other library words in the sentence, reviewed
   with the bulk-add list. Until then a gap can be asked for its meaning, not for the
   gap or the reading.

## Exercises (#99)

- Still `EntryExercise`s over vocabulary collections, with a new `settings` member,
  `sentence.choice`. **The item is the word**, so the deck, reviews, history and
  per-item statistics work unchanged.
- **Each question picks a sentence of the word:** active, with a gap linked to it,
  rotating among them. Deactivate a sentence to leave it out. Words without a usable
  sentence aren't asked, and the form says how many there are.
- Directions:
  - **fill the gap** (sentence with a gap → word);
  - **reading** (highlighted word → its reading in context);
  - **meaning** (highlighted word → meaning; linked gaps only).

  The translation can be shown or hidden.
- **Fill-the-gap options are real gaps:** the surfaces of gaps of other words of the
  pool with the same pos and inflection (引かれた among 飲まれた, 押された). All options
  share the form, so the ending doesn't give the answer away, and no conjugation
  engine is needed. With too few, fewer options, down to 2; with fewer still, the word
  isn't asked in that direction. Forms are never mixed. The ambiguity rule and the
  comparison keys of [exercises](../technical/exercises.md) apply.
