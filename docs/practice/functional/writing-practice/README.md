# Writing Practice

[← Functional documentation](../README.md)

How a user learns to write the kanji and words in their library, and the kana, before
the exercises or as a review during them.

## What it is

Writing practice shows a character's stroke order and lets the user draw it over the
model. It works for kanji, for hiragana and katakana, and for whole words. It is a warm-up, not a test: nothing is graded or stored, and it doesn't count
in the statistics. Handwriting [exercises](../exercises/README.md) are what test
whether the user can write a kanji from memory.

## Modes

- **Guided.** The kanji is shown in grey. The next stroke draws itself over and over,
  starting from a red dot. The user traces it: if the stroke follows the model, it
  snaps into place and the next one is shown; if not, it is wiped with a hint ("start
  at the red dot", "backwards"). After three misses on a stroke the user can skip it.
- **Guided, then free** (the default). Each kanji is guided once, then drawn freely a
  number of times (2 by default, from 1 to 5).
- **Free.** The user draws the whole kanji over its model, or hides the model and
  draws from memory. Checking lays the drawing over the model, strokes numbered, so
  the user sees where it strays. There is no score.

A **word** is written one character after another: a row of cells above the pad
shows the word, the character being drawn and the ones done, and a done character can
be drawn again by tapping its cell. The word is written as the library shows it: its
first spelling that isn't hidden, okurigana included (食べる), or its reading for a
kana word. Its reading is shown with it.

After each drawing the user can do it again or go on. The mode can be changed during
the practice; the current kanji starts over in the new mode. A character that has no
stroke order (KanjiVG doesn't cover it) is shown and passed over.

## Where to start it

- **Practicar** in the sidebar: choose Kanji, Palabras or Kana. For kanji and words,
  pick one or more collections or the whole library; only active items are
  practised, and one in several collections comes up once. For kana, pick rows of the
  hiragana and katakana tables (the あ row, the か row…, the voiced rows and the small
  kana); they don't need to be in the library. Then the mode, the free repetitions
  and whether to shuffle.
- **Practicar** on a kanji of the library: that kanji alone.
- **Practicar escritura** on a word of the library: that word alone.
- **Practicar** on a collection: the practice screen with that collection chosen.
- **During a handwriting exercise**: once a drawing is graded, "Practicar kanji"
  opens the kanji asked for in a window over the session. Closing it goes back to
  the session exactly where it was. The session review offers the same for each
  drawing.

## Later

Handwriting exercises for words, graded like the kanji ones, are planned (#67).
