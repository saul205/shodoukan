# Exercises

[← Functional documentation](../README.md)

How a user practises the words and kanji of their collections. Exercises are created,
managed and played in the practice app ("Ejercicios"); the history and the
statistics are built in the practice API, and their screens come in the next phases
(see the
[design](../../technical/exercises.md#phases)).

## What an exercise is

An exercise is a saved way of practising: **which collections** it draws from, **what
kind of exercise** it is, and **what is studied**. The user creates it once and starts
it as often as they like; each run is a **session**, and every session is kept so the
user can look back at how it went.

An exercise works on either words or kanji, never both, like collections. It draws
from one or more collections of that kind; an item in several of them counts once.

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

## Playing a choice card

"Empezar" on an exercise opens a **session**, and the user studies for as long as
they like: there's no set number of questions. Meanings are shown in the language
chosen in the sidebar when the session starts. The header counts the answers and the
right ones.

1. An active item from the collection is shown with the fields of the direction.
2. Below it, the options: the right one and wrong ones taken from other items of the
   collection.
3. The user picks one, with a click or its number key (1–4…). The card turns over
   and shows the back. The picked option turns red if it was wrong, and the right one
   green.
4. From the back the user can open the item's full detail in a window, without
   leaving the session; the wrong options can open theirs too.
5. "Saltar" (or the S key) skips a card the user doesn't know: it counts as a miss,
   the card turns over showing the right option, and it comes back a few cards
   later like any missed one.
6. "Siguiente" (or Enter) brings the next card, until the user stops with "Terminar".
   If the collections no longer have enough active items for another card, the
   session says so and can be finished.

**Which item comes next.** Every item of the collection comes up once, in random
order, before any repeats; then a new round starts, shuffled again. An item answered
wrong comes back a few cards later, without taking every turn when there are many
misses. The same item never comes twice in a row. Items added to the collection, or
deactivated, during the session count from the next card.

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

**A word is asked by its usual form.** Words often have variant spellings or
readings (山 also read ヤマ, 川 also がわ). The card asks and offers only the first one
the user has enabled, which is the usual one; the back of the card shows them all. To
be asked another form, disable the first one in the library. Kanji are different: each
on'yomi and kun'yomi is worth learning, so any of them can be asked.

**Ending a session.** The session ends when the user finishes it ("Terminar"). Leaving
the page doesn't end it: until then, "Continuar" on the exercise list or the home page
brings the user back to the same card. It ends on its own when any exercise is started
again (the app asks first) or after 30 minutes without activity, counted until the
last answer. The card on screen when it ends isn't counted. A finished session shows
how it went and offers to practise again.

Each card is answered once: a second click on another option doesn't change the
answer.

## History and statistics

Every session keeps each question as it was shown, the option picked and whether it
was right. Editing or removing an item later doesn't change past sessions. The history
and the statistics below are available in the practice API; their screens come in
the next phases (continuing a session is already in the app).

- **Continue:** a session left open (the tab was closed) can be resumed from the
  exercise list or the home page, as long as it isn't idle.
- **History:** each exercise lists its past sessions (date, duration, questions
  answered, accuracy), and any of them can be reviewed card by card, or only the
  missed ones.
- **Statistics:** for each exercise, its accuracy overall and per direction, and the
  items missed most; a statistics page shows the same over all exercises (words and
  kanji missed most apart), plus the answers of each of the last days, counted in the
  user's time zone, and a summary per exercise. Missed items show their current name
  in the library; items removed from it aren't listed, and neither are deleted
  exercises in the per-exercise summary.

## Managing exercises

- **Create** an exercise with a name, an optional description, its collections, the
  directions, the back fields and the number of options.
- **See** their exercises, sorted by name.
- **Edit** any of it except whether it holds words or kanji.
- The form checks the same rules before saving: at least one collection and one
  direction, no direction asking a field it shows, no repeated direction. Switching
  between words and kanji while creating starts the collections and fields over,
  since they belong to one kind.
- **Delete** it. Its past sessions are kept in the history.

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
| The collections have fewer than 2 usable items (active, with the fields the exercise asks), or the exercise has no collection left | The session can't start |
| A card is answered again, or the session has ended | Rejected; the first answer counts |
| The collection loses its usable items during a session | No more cards; the user can finish the session |

Technical details: [exercises design](../../technical/exercises.md) and
[endpoints](../../technical/api/endpoints.md#exercises).
