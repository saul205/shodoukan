# Customising the Library

[← Functional documentation](../README.md)

How a user adapts a word or kanji in their library to the way they study it.

## The detail page

Opening an item of the library shows the user's copy: readings, meanings, examples,
notes, and the collections it's in. Everything below is saved as soon as the user
makes the change.

Meanings are shown in the language chosen in the side menu. A word only shows the
meaning groups (senses) that have a meaning in that language: the others belong to
other languages and appear when the user switches to one of them.

A word's page shows **its kanji** as on the dictionary, each one ready to import or to
put in a collection from the card's corner, plus **Import the N missing** when more than
one isn't in the library yet. A kanji already in the library opens the user's copy.

A kanji's page also lists a few **words that use it**, taken from the dictionary. Words
already in the library are ticked and open the user's copy; the others open the
dictionary. When there are more, a link goes to the dictionary's page for the kanji,
which lists them all.

## What the user can change

- **Hide what they don't need.** Any reading, spelling, meaning or example can be
  disabled, and enabled again later. A disabled part stays visible on the detail page
  (greyed out) but is left out when practising.
- **Add their own meanings.** Words get them per meaning group (sense), kanji on the
  kanji. The user's meanings are marked as their own, and they can edit or delete them.
- **Write notes.** A general note on the word or kanji, and for words one note per
  meaning group. Notes are free text up to 2000 characters; emptying a note removes it.
- **Deactivate the item.** It stays in the library and in its collections, but isn't
  practised until it's activated again.
- **Remove it from the library.** The copy, its notes and customisations are deleted,
  and it leaves every collection. The dictionary entry is untouched and can be imported
  again (as a fresh copy).

## What the user can't change

The dictionary's own data is never edited or deleted: readings, spellings, examples
and the dictionary's meanings can only be disabled. That way nothing original is ever
lost, and re-enabling it is always possible. Adding readings of their own isn't
possible yet.

## When it doesn't work

| Situation | Result |
|---|---|
| Not signed in, or the session expired | Rejected; the user must sign in again |
| The item isn't in the user's library | Rejected as not found |
| Editing or deleting one of the dictionary's meanings | Rejected; it can only be disabled |
| An empty meaning, or a note over 2000 characters | Rejected as invalid |

Technical details: [use cases](../../technical/application/use-cases.md) and
[endpoints](../../technical/api/endpoints.md#library-items-detail-and-customisation).
