# Creating Words of Your Own

[← Functional documentation](../README.md)

How a user adds a word the dictionary doesn't have to their library.

## Why

Some words are never listed together in the dictionary even though each part is
there: a number with its counter (三匹, 二枚, 五本), a set phrase from class, a word from
a dialect. The user creates them themselves and studies them like any other word.

## What the user does

- From the library, **Nueva palabra**; from a word collection, **Nueva palabra
  propia** in its menu (the new word goes into that collection).
- They write its **spelling** (optional: a word written only in kana has none; several
  can be separated with commas, the usual one first), its **reading** in hiragana or
  katakana (one at least), and its **first meaning** in the language chosen in the side
  menu.
- While they type, if the dictionary already has a word written (or, without a
  spelling, read) the same way, the form says so and links to it, so they can import it
  instead. It's only a warning: they can still create theirs.
- **Crear palabra** adds it and opens its page.

## What they get

The word works like an imported one: it can get more meanings and meaning groups,
examples, notes, collections, and be practised in exercises and in writing practice
(its kanji are drawn with the dictionary's stroke order). Its page is marked **palabra
propia**, lists the kanji of its first spelling as the dictionary has them, and has no
link to the dictionary.

Everything in it is the user's own, so all of it can be changed: spellings and readings
are added and deleted on the page (a word keeps at least one reading). Any imported
word can also take spellings and readings of the user's own, marked **propio**.

## When it doesn't work

- A reading that isn't kana, or a missing reading or meaning: **Crear palabra** stays
  disabled and the form says what's missing.
- Removing a word of your own from the library deletes it for good: it isn't in the
  dictionary to import again. The page warns before removing it.
