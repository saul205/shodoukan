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
- **Add** items from their library to a collection, and **remove** them. The window
  for adding lists only what isn't in the collection yet, with the same search as the
  library ([searching](../library/browse.md#searching)); the user can search several
  times and add everything they ticked at once. Adding something that's already
  there, or removing something that isn't, changes nothing, so a double click or a
  retry is safe.
- **Browse** a collection's items, page by page, in the order they were added, and
  **search** within them, best match first. Deactivated items are listed too, marked
  as inactive, so the user can find and reactivate them; the list can be narrowed to
  only active or only deactivated items, as in the library. Practice only uses the
  active ones.

## Exporting and importing

A collection can be **downloaded as a file** and **imported back**, into the same
account or another one (to move it, keep a copy, or give it to someone).

- **What the file has:** the collection's name and description, and its items, active
  or not, with everything the user did to them: their own meanings, senses, spellings,
  readings and examples, their notes, and what they hid. Not the dictionary's data
  itself (that's taken from the dictionary again when importing), nor exercises or
  their history.
- **Importing always creates a new collection.** If the name is in use, a number is
  added: "N5 (2)".
- **What the user already has stays as it is.** A word or kanji already in the library
  is reused: it gets the meanings, examples, ... of the file that it doesn't have yet,
  and the file's notes only if it has none; what the user hid or deactivated doesn't
  change. Items that weren't in the library are imported as the file has them
  (hidden parts, notes, active or not).
- **Importing the same file again duplicates nothing**: it creates another collection
  with the same items, and adds no meaning or word twice.
- **A collection imported from a file is the user's alone**: it's never updated, and
  what it brought stays even if a public collection with the same words later drops
  it.
- **If someone changed something along the way, both versions are kept.** For example,
  if a meaning the user wrote was edited by whoever passed the collection on, the
  edited one is added next to the user's own: nothing is lost, and the user can delete
  the one they don't want.
- A word the dictionary no longer has is left out, and the user is told which ones.
  A meaning or example the user added to a sense the dictionary has since changed is
  left out too.
- A damaged or edited file that isn't valid (for example, one that lists the same word
  or kanji twice) imports nothing at all. A file of kanji
  can't be imported as words, and the other way round.
- A collection of more than 5000 items can't be exported.

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
they simply don't exist, unless their owner publishes them
([sharing collections](share.md)).

## When it doesn't work

| Situation | Result |
|---|---|
| Not signed in, or the session expired | Rejected; the user must sign in again |
| The collection doesn't exist (or was deleted) | Rejected as not found |
| The item isn't in the user's library | Rejected as not found |
| The name is already used by another collection of that kind | Rejected; choose another name |
| The name is empty or longer than 100 characters | Rejected as invalid |
| The imported file isn't valid, or is of the other kind | Rejected; nothing is imported |

Technical details: [use cases](../../technical/application/use-cases.md) and
[endpoints](../../technical/api/endpoints.md#collections).
