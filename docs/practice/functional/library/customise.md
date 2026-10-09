# Customising the Library

[← Functional documentation](../README.md)

How a user adapts a word or kanji in their library to the way they study it.

## The detail page

Opening an item of the library shows the user's copy: readings, meanings, examples,
notes, and the collections it's in. The folder icon beside **Collections** adds it to
another one: it searches the collections it isn't in yet, and typing a new name offers
**Create "…"**, which creates the collection with the item in it. Everything below is saved as
soon as the user makes the change.

Meanings are shown in the language chosen in the side menu. A word only shows the
meaning groups (senses) that have a meaning in that language: the others belong to
other languages and appear when the user switches to one of them.

A word's page shows **its kanji** as on the dictionary, each one ready to import or to
put in a collection from the card's corner, plus **Import the N missing** when more than
one isn't in the library yet. A kanji already in the library opens the user's copy.

A kanji's page also lists a few **words that use it**, taken from the dictionary. Words
already in the library are ticked and open the user's copy; the others open the
dictionary. A link searches the dictionary for the kanji, which finds the words that
start with it, as on Jisho.

## What the user can change

- **Hide what they don't need.** Any reading, spelling, meaning or example can be
  disabled, and enabled again later. A disabled part stays visible on the detail page
  (greyed out) but is left out when practising. A word's whole meaning group (sense)
  can be hidden with one switch too; enabling it again brings it back as it was, with
  the meanings and examples the user had hidden inside it still hidden.
- **Add their own meanings.** Words get them per meaning group (sense), kanji on the
  kanji. The user's meanings are marked as their own, and they can edit or delete them.
- **Add their own examples.** Each meaning group has **Añadir un ejemplo propio**: a
  sentence in Japanese and, optionally, its translation in the language chosen in the
  side menu. To add one to a sense the dictionary doesn't have, the user first creates
  that meaning group. Their examples are marked as their own and can be rewritten (the
  translation in the current language; translations written in other languages stay)
  or deleted.
- **Add their own spellings and readings.** Beside a word's spellings and readings, a
  box adds one of the user's own (readings in kana), marked as their own and deletable.
  A word always keeps at least one reading. Words of the user's own are made of these
  (see [creating words of your own](create.md)).
- **Add their own meaning groups.** Under a word's meanings, **Nuevo significado**
  creates a group of the user's own with its first meaning (in the language chosen in
  the side menu), for a sense the dictionary doesn't cover. It takes more meanings and a
  note like any other, and deleting it (after confirming) takes its meanings and note
  with it.
- **Write notes.** A general note on the word or kanji, and for words one note per
  meaning group. Notes are free text up to 2000 characters; emptying a note removes it.
- **Deactivate the item.** It stays in the library and in its collections, but isn't
  practised until it's activated again.
- **Remove it from the library.** The copy, its notes and customisations are deleted,
  and it leaves every collection. The dictionary entry is untouched and can be imported
  again (as a fresh copy).

## What the user can't change

The dictionary's own data is never edited or deleted: readings, spellings, examples
and the dictionary's meaning groups and meanings can only be disabled. That way nothing original is ever
lost, and re-enabling it is always possible.

## When it doesn't work

| Situation | Result |
|---|---|
| Not signed in, or the session expired | Rejected; the user must sign in again |
| The item isn't in the user's library | Rejected as not found |
| Editing or deleting one of the dictionary's meanings | Rejected; it can only be disabled |
| An empty meaning, or a note over 2000 characters | Rejected as invalid |

Technical details: [use cases](../../technical/application/use-cases.md) and
[endpoints](../../technical/api/endpoints.md#library-items-detail-and-customisation).
