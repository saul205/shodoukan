# Managing Collections

[← Functional documentation](../README.md)

How a user groups the words and kanji in their library into collections.

## What a collection is

A collection is a named group of items from the user's library, such as "verbs",
"JLPT N5" or "kitchen words". It doesn't copy anything: the items stay in the library
and the collection only points at them. So one item can be in several collections, and
customising an item shows up in every collection it's in.

Collections also work as **tags**: putting a word in "verbs" is the same as tagging it
"verbs".

There are two kinds, and they never mix:

- **Word collections** hold imported words (entries).
- **Kanji collections** hold imported kanji.

## What the user can do

- **Create** a collection with a name and, optionally, a description. It starts empty.
- **See their collections** of each kind, sorted by name.
- **Rename** a collection or change its description.
- **Delete** a collection. Its words or kanji stay in the library; only the grouping
  goes away.
- **Add** an item from their library to a collection, and **remove** it. Adding
  something that's already there, or removing something that isn't, changes nothing,
  so a double click or a retry is safe.
- **Browse** a collection's items, page by page, in the order they were added.
  Deactivated items are listed too, marked as inactive, so the user can find and
  reactivate them; the list can be narrowed to only active or only deactivated items,
  as in the library. Practice only uses the active ones.

Only items in the library can be in a collection. A dictionary word that isn't
imported yet can be put in a collection directly: it's imported and added in one go,
and if the collection can't be used nothing is imported
([importing](../library/import.md)).

## Names

- A name is 1 to 100 characters; spaces at the start and end are ignored.
- A user can't have two word collections, or two kanji collections, with the same
  name. A word collection and a kanji collection may share one (e.g. "N5" for both).
- Different users' names never clash.

## Privacy

Collections are personal. Nobody else can see, change or add to them; to anyone else
they simply don't exist.

## When it doesn't work

| Situation | Result |
|---|---|
| Not signed in, or the session expired | Rejected; the user must sign in again |
| The collection doesn't exist (or was deleted) | Rejected as not found |
| The item isn't in the user's library | Rejected as not found |
| The name is already used by another collection of that kind | Rejected; choose another name |
| The name is empty or longer than 100 characters | Rejected as invalid |

Technical details: [use cases](../../technical/application/use-cases.md) and
[endpoints](../../technical/api/endpoints.md#collections).
