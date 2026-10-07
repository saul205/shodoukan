# Writing Practice

[← Functional documentation](../README.md)

How a user learns to write the kanji in their library, before the exercises or as a
review during them.

## What it is

Writing practice shows a kanji's stroke order and lets the user draw it over the
model. It is a warm-up, not a test: nothing is graded or stored, and it doesn't count
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

After each drawing the user can do it again or go on. The mode can be changed during
the practice; the current kanji starts over in the new mode. A character that has no
stroke order (KanjiVG doesn't cover it) is shown and passed over.

## Where to start it

- **Practicar** in the sidebar: pick one or more kanji collections, or the whole
  library, the mode, the free repetitions and whether to shuffle. Only active kanji
  are practised, and a kanji in several collections comes up once.
- **Practicar** on a kanji of the library: that kanji alone.
- **Practicar** on a kanji collection: the practice screen with that collection
  chosen.
- **During a handwriting exercise**: once a drawing is graded, "Practicar kanji"
  opens the kanji asked for in a window over the session. Closing it goes back to
  the session exactly where it was. The session review offers the same for each
  drawing.

## Later

Practising words (one character after another, kana included) and the hiragana and
katakana tables is planned (#66), and so are handwriting exercises for words (#67).
