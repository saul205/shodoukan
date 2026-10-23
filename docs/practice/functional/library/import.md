# Importing into the Library

[← Functional documentation](../README.md)

How a user adds a dictionary word or kanji to their personal practice library.

## What the user does

While browsing the dictionary, the user clicks **Import** on an entry (a word such as
食べる) or on a kanji (such as 食). In the search results it's the **+** icon in the
card's top-right corner (a tooltip says what it does); on a word's or kanji's detail
page it's a labelled button. It's added to their library, ready to customise,
group into collections and practise with.

Entries and kanji are imported separately: importing a word doesn't import its kanji,
and importing a kanji doesn't import words that use it. A word's page lists its kanji
with the same import button on each, so the user can pick the ones they want to study
without leaving the word (兄 and 弟 from 兄弟, *kyoudai*). When more than one is missing,
**Import the N missing** adds them all at once.

## What gets copied

The library keeps **its own copy** of the item, taken at the moment of import:

- **Entries:** spellings, readings, every meaning in **every language** the dictionary
  has, parts of speech, notes, examples with their translations, JLPT level and
  whether the word is common.
- **Kanji:** on and kun readings, name readings (nanori), meanings in every language,
  school grade, stroke count, frequency and JLPT level.

Everything starts enabled and marked as *imported*. Later dictionary updates don't
change the copy, so the user's customisations are never overwritten. Some dictionary
details aren't copied because practice doesn't use them: frequency tags,
cross-references between words, and where an example sentence came from.

## Importing straight into a collection

Next to the import button there's a **folder** button. It opens the user's collections
of that kind (word collections for a word, kanji collections for a kanji) with a search
box, and ticks the ones the item is in, like saving a song to a playlist:

- If the item **isn't imported yet**, picking a collection imports it and puts it in
  that collection at once. If that can't be done (say the collection was just deleted
  elsewhere), nothing is imported, so the user never ends up with half of it.
- If it's **already imported**, picking adds it to the collection and unticking takes
  it out; it stays in the library either way.
- **Typing a name that doesn't exist** offers **Create "…"**: it creates that collection
  and puts the item in it (importing it first if needed). Its description, if wanted, is
  added later on the collections page.

## Seeing what's already imported

On the dictionary page, every result shows whether it's already in the user's
library: imported results show a green **✓** ("In your library") instead of **+**.
Searching works the same for everyone, signed in or not; the import status is only
shown to a signed-in user.

## Removing from the dictionary

Hovering over (or tabbing to) the **✓** turns it into a red **remove** button. Clicking
it asks for confirmation, because removing deletes the user's notes and own meanings
and takes the item out of every collection, exactly like removing it from the library
page. Once removed, the result shows **+** again and can be imported anew. On the
detail pages, **Open in your library** next to the button goes to the library copy.

## Importing twice

Importing something already in the library does nothing harmful: the user gets the
copy they already have, unchanged. A double click or a retry is safe.

Each user has their own copy. Two users importing the same word get two independent
copies.

## When it doesn't work

| Situation | Result |
|---|---|
| Not signed in, or the session expired | Rejected; the user must sign in again |
| The word or kanji isn't in the dictionary | Rejected as not found |

Technical details: [use cases](../../technical/application/use-cases.md) and
[endpoints](../../technical/api/endpoints.md).
