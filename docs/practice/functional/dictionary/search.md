# Searching the Dictionary

[← Functional documentation](../README.md)

How a user finds words and kanji to study.

## What the user does

On the dictionary page, the user types a word in any of these forms:

| Typed | Example | Finds |
|---|---|---|
| Kanji | 食べる, 食 | words written with it, and those kanji |
| Kana | たべる, みず | words read that way |
| Romaji (Hepburn) | taberu | words read that way, and words with that meaning |
| A meaning | water, comer | words whose meaning matches, in the chosen language |

Results show matching **words** (a page at a time, the most useful first) and the
related **kanji**. Each word shows its spellings, readings, meanings, notes, examples,
JLPT level and whether it's common.

Searching doesn't need an account. When the user is signed in, each result also shows
whether it's already in their library: see
[importing into the library](../library/import.md#seeing-whats-already-imported).

## Meaning language

The user picks the language meanings are searched in (English by default; also
Spanish, French, German and others the dictionary has). Results keep their meanings
in every language, and the page shows the user's language.

## Relationship with the dictionary site

The practice app searches the same dictionary as the shodoukan dictionary site and
finds the same results. The two apps are independent: the practice app doesn't need
the dictionary site to be running.

Technical details: [endpoints](../../technical/api/endpoints.md#get-dictionarysearch).
