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

Technical details: [use cases](../../technical/application/use-cases.md) and
[endpoints](../../technical/api/endpoints.md#get-libraryentries-and-get-librarykanji).
