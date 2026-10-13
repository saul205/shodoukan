# Sharing Collections

[← Functional documentation](../README.md)

How a user makes a collection public, and how others find it and add it to their
library.

## Publishing

- From "Mis colecciones", the owner **publishes** a collection. What gets published is
  a **version**: a snapshot of the collection as it is now. Later changes to the
  collection or its words aren't seen until the owner publishes a new version (v2,
  v3, …), so they decide when it's ready.
- Only the **active** items are published. The owner's **notes** go only if they tick
  "Incluir mis notas" (they're off by default: notes are often personal). Everything
  else the owner added to the words (their own meanings, examples, spellings and
  readings) and what they hid go with them.
- The owner can **stop sharing** it at any time. Nobody can find or import it then,
  but what others already imported stays theirs. Publishing it again brings back its
  downloads.
- A collection of more than 5000 active items can't be published.

## Finding collections

- "Colecciones públicas" lists the public collections, words and kanji apart. It can
  show the user's own (**Mías**), everybody else's (**De otros**) or all.
- The **search** looks in the collection's name, its description and the owner's
  username.
- They're sorted by **popularity** (how many people downloaded them) or by **date**.
- Each one shows its owner, version, how many items it has, how many people
  downloaded it, and whether the user already imported it (and which version).

## Looking before importing

A public collection can be **browsed page by page** before importing it, each word or
kanji as the owner shares it: what the dictionary says, plus what the owner added and
hid. Opening one shows it whole, read-only: the meanings, senses, examples, spellings
and readings the owner added are marked "de <owner>", and their notes "Nota de
<owner>". The user's own data is never mixed in: items they already have are only
marked **En tu librería** (on importing, those keep the user's data and just gain
what's new).

## Importing

- **Importar a mi librería** adds the collection's latest version to the user's
  library as a **new collection** of theirs, with the same rules as importing a file
  ([managing collections](manage.md#exporting-and-importing)): what the user already
  has is reused and keeps their choices, nothing is duplicated, and words the
  dictionary no longer has are left out.
- It counts as **one download per person**: importing it again, or importing one's own
  collection, doesn't add to the count.
- The copy is the user's: they can change it freely. It remembers where it came from
  and which version, for updating it later when its owner publishes a new one (coming
  soon).

## Privacy

- A collection is private until its owner publishes it. Private collections don't
  exist for anyone else.
- Other users see the owner's **username** (not their email).
- Notes are only shared if the owner chooses so when publishing.

Technical details: [use cases](../../technical/application/use-cases.md#commands-commandspublic_collection_commandspy)
and [endpoints](../../technical/api/endpoints.md#public-collections). Design:
[proposal](../../proposals/library-authoring-and-sharing.md#sharing-public-collections-82-88-89-90).
