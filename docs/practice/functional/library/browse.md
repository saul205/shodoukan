# Browsing the Library

[← Functional documentation](../README.md)

How a user sees everything they've imported.

## What the user sees

The library has two lists: **words** (imported entries) and **kanji**. Each shows the
user's own copies, most recently imported first, page by page, with the total number
of items so the user knows how many pages there are.

Each item shows its full copy (readings, meanings, examples...) and whether it's
active. Deactivated items are listed too, so the user can find and reactivate them;
the list can also be narrowed to only active or only deactivated items.

## Searching

A search box above the list finds items as the user types, by:

- **Spelling or reading:** kanji (食べる, 食), kana (たべる, パン) or romaji, which is
  turned into kana (`taberu`, `pan`). Kanji are also found by their on and kun readings
  (`kai` → 会), and a word finds its kanji (兄弟 → 兄 and 弟).
- **Meaning**, in the language chosen in the side menu, including the user's own
  meanings (`eat`, `comer`).

Readings and meanings the user has hidden still count: hiding is for practice, and the
user still needs to find the item. The best matches come first: something that is
exactly the search, then something that starts with it (or has a meaning with a word
that does: "to eat" for `eat`), then something that contains it. The search is kept
when switching between words and kanji, and in the address, so going back returns to
it. A search in romaji that is also an English word (`same`) finds both: the word read
さめ and the one meaning "same".

## Building collections

This is where the user picks items to put in a collection: from the words list into a
word collection, from the kanji list into a kanji collection
([managing collections](../collections/manage.md)). To add something not yet in the
library, import it from the dictionary first ([importing](import.md)).

## Privacy

Each user only ever sees their own library.

## When it doesn't work

| Situation | Result |
|---|---|
| Not signed in, or the session expired | Rejected; the user must sign in again |
| A page size over 100 items | Rejected as invalid |
| A search over 100 characters | Rejected as invalid |
| Nothing matches the search | An empty list saying so |

Technical details: [use cases](../../technical/application/use-cases.md) and
[endpoints](../../technical/api/endpoints.md#get-libraryentries-and-get-librarykanji).
