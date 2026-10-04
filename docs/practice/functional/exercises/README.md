# Exercises

[← Functional documentation](../README.md)

How a user practises the words and kanji of their collections. Saving exercises is
built; playing them and their history come in the next phases (see the
[design](../../technical/exercises.md#phases)).

## What an exercise is

An exercise is a saved way of practising: **which collections** it draws from, **what
kind of exercise** it is, and **what is studied**. The user creates it once and starts
it as often as they like; each run is a **session**, and every session is kept so the
user can look back at how it went.

An exercise works on either words or kanji, never both, like collections. For now it
uses one collection; several collections of the same kind will come later.

## Kinds of exercise

The first kind is the **choice card**: a card shows something about an item and the
user picks the right answer among several options (4 by default).

Planned kinds, sharing the same structure: a plain card the user flips and marks as
known or not, a card where the user types the answer, handwriting a kanji, and
sentences with gaps to fill with kanji given the kana.

## What is studied: fields and directions

Each item has fields:

- **Words:** writing (食べる), reading (たべる), meaning (to eat).
- **Kanji:** the kanji (食), on'yomi (ショク), kun'yomi (た.べる), meaning (eat).

The user chooses one or more **directions**, each "show these fields → ask for this
one". For example:

- Words: *meaning → writing* (see "to eat", pick 食べる) and *writing → meaning*.
- Kanji: *kanji → on'yomi*, *kanji → kun'yomi* and *kun'yomi → kanji*. Here the
  on'yomi is studied but never shown on the card: it only appears among the options.

Each question uses one of the chosen directions at random.

The user also chooses what the **back** of the card shows once answered, besides the
question and its answer: for example the reading and the meaning.

## Playing a choice card (next phases)

1. A random active item from the collection is shown with the fields of the
   direction.
2. Below it, the options: the right one and wrong ones taken from other items of the
   collection.
3. The user picks one. The card turns over and shows the back. The picked option turns
   red if it was wrong, and the right one green.
4. From the back the user can open the item's full detail in a window, without
   leaving the session.

Example, direction *kanji → kun'yomi*:

| Front | Back |
|---|---|
| 食 | 食 · たべる · eat |
| あるく · みち · **たべる** · すこし | あるく (picked, red) · みち · たべる (right, green) · すこし |

**A wrong option is never also right.** Many words share a reading and many kanji
share an on'yomi, so before offering an option the app checks that it isn't a valid
answer too: two kanji read はし, two words meaning "to speak", the same reading written
in katakana or hiragana. If the collection doesn't have enough suitable items, the
question has fewer options.

Only active items with enabled parts are used: a reading or meaning the user hid isn't
shown or asked, and a word with no kanji isn't asked for its writing.

## History (next phases)

Every session keeps each question as it was shown, the option picked and whether it
was right, so the user can review past sessions and see which items they miss most.
Editing or removing an item later doesn't change past sessions.

## Managing exercises

- **Create** an exercise with a name, an optional description, a collection, the
  directions, the back fields and the number of options.
- **See** their exercises, sorted by name.
- **Edit** any of it except whether it holds words or kanji.
- **Delete** it. Its past sessions will be kept in the history.

Deleting a collection removes it from its exercises; an exercise with no collection
left can't be started until it gets one.

## Privacy

Exercises and sessions are personal, like collections: nobody else can see them, and
a collection of someone else's can't be used.

## When it doesn't work

| Situation | Result |
|---|---|
| Not signed in, or the session expired | Rejected; the user must sign in again |
| The exercise or the collection doesn't exist, isn't the user's, or is of the other kind (a word collection in a kanji exercise) | Rejected as not found |
| A field that doesn't exist for the item kind, a direction that asks for a field it shows, or a repeated direction | Rejected as invalid |
| No directions, or no collection | Rejected as invalid |
| The collection has fewer than 2 usable items (next phases) | The session can't start |

Technical details: [exercises design](../../technical/exercises.md) and
[endpoints](../../technical/api/endpoints.md#exercises).
