# Importing into the Library

[← Functional documentation](../README.md)

How a user adds a dictionary word or kanji to their personal practice library.

## What the user does

While browsing the dictionary, the user clicks **Import** on an entry (a word such as
食べる) or on a kanji (such as 食). It's added to their library, ready to customise,
group into collections and practise with.

Entries and kanji are imported separately: importing a word doesn't import its kanji,
and importing a kanji doesn't import words that use it.

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

## Seeing what's already imported

On the dictionary page, every result shows whether it's already in the user's
library. Results already imported have their **Import** button disabled; the rest can
be imported. Searching works the same for everyone, signed in or not; the import
status is only shown to a signed-in user.

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
