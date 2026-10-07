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

- **Choice card:** a card shows something about an item and the user picks the right
  answer among several options (4 by default).
- **Writing by hand:** the card shows something about an item and the user writes the
  answer by hand, stroke by stroke. In a kanji exercise that's the kanji (see
  [writing the kanji](#writing-the-kanji)); in a word exercise, the word's spelling
  or its reading, a character per box (see [writing a word](#writing-a-word)).

Planned kinds, sharing the same structure: a plain card the user flips and marks as
known or not, a card where the user types the answer, and sentences with gaps to fill
with kanji given the kana.

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
   leaving the session; the wrong options can open theirs too. From there, "Abrir en
   la librería" goes to the item's library page (to edit it, for instance), and its
   back button returns to the session where it was.
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

## Writing the kanji

A session of a handwriting exercise works like a choice card's (the same order of
cards, missed ones coming back, "Saltar", "Terminar"), but the answer is a drawing.

1. The top of the screen shows what's asked (for example the meaning "one") and the
   rest is a square to draw in, with a finger, a pen or the mouse.
2. The user draws the kanji, stroke by stroke, in its stroke order. "Deshacer"
   (Backspace, Ctrl+Z) removes the last stroke and the eraser clears the drawing.
3. "Comprobar" (Enter) sends it. The app compares it with the kanji's strokes, as
   [KanjiVG](https://kanjivg.tagaini.net/) draws them in Japanese order (the same as
   the stroke order on the kanji pages), and says:
   - **¡Correcto!**: every stroke is there, in order, in the right direction, and the
     drawing looks like the kanji. Strokes a bit out of place, or longer or shorter
     than they should be, are pointed out but don't count against it: nobody writes
     as exactly as the model;
   - **Mejorable**: it's the kanji, but a stroke is backwards or out of order, or one
     is missing in a kanji of 5 strokes or more. It counts as right, but the kanji
     comes back later to practise;
   - **Fallada**: it's another kanji, or too far from it.
4. Next to the drawing, the kanji with its strokes numbered, and what was wrong with
   each stroke. On a phone the two are shown overlaid (or one at a time); the card
   with its back is under "Ver tarjeta".

Where and how big the kanji is drawn in the square doesn't matter, only its shape.
If several kanji of the collections fit what's asked (two kanji read はし), any of
them is right. Kanji without a stroke order in the dictionary aren't asked; a
collection needs at least 2 that have one.

## Writing a word

In a word exercise written by hand, each direction asks for the word's **spelling**
(食べる, with its okurigana) or its **reading** (たべる, in kana). Asking for the
reading is how words written only in kana (これ) and the kana themselves are
practised.

1. The top of the screen shows what's asked (for example the meaning "to eat"), and
   below it a box per character of the word: as many boxes as it has characters. On
   a computer they're in a row; on a phone, in two columns. If they'd be too small
   (a long word on a phone) one box is shown at a time, with buttons to move between
   them.
2. The user writes a character in each box, in any order. "Deshacer" and the eraser
   act on the box last written in.
3. "Comprobar" (Enter) sends the whole word. Each character is compared with its
   stroke order like a kanji, and the word gets the worst verdict of its characters:
   one wrong character makes the word wrong. The score is the average.
4. Each character is shown with the user's drawing over it, coloured stroke by
   stroke, and its score; choosing one shows it next to the model, with what was
   wrong. "Practicar palabra" opens the word in the writing practice.

Words with a character without a stroke order, or longer than 12 characters, aren't
asked. If several words of the collections fit what's asked and have as many
characters, any of them is right.

## History and statistics

Every session keeps each question as it was shown, the option picked and whether it
was right. Editing or removing an item later doesn't change past sessions.

- **Continue:** a session left open (the tab was closed) can be resumed from the
  exercise list or the home page, as long as it isn't idle.
- **History:** opening an exercise (its name in the list) shows what it studies and
  its past sessions, newest first (date, duration, questions answered, accuracy, open
  or finished). Any of them opens: a finished session shows its result and a review:
  one line per card (the question, the right answer, the wrong pick struck through,
  how long it took; for a drawing, a small copy of it) that unfolds into the card as it
was played, with the drawing next to the kanji; all of them, or only
  the missed and skipped ones. Sessions of a deleted exercise can still be reviewed.
- **Statistics:** each exercise's page shows, once it has answers, its totals
  (sessions, answers, accuracy, mean time), its accuracy per direction and the items
  missed most (each opens its detail). "Estadísticas" in the sidebar shows the same
  over all exercises (words and kanji missed most apart), plus the answers of each of
  the last 7, 30 or 90 days, counted in the user's time zone, and a summary per
  exercise. Missed items show their current name
  in the library; items removed from it aren't listed, and neither are deleted
  exercises in the per-exercise summary.

## Managing exercises

- **Create** an exercise with a name, an optional description, its collections, the
  kind (for kanji: choose the answer, or write the kanji), the directions, the back
  fields and, for a choice card, the number of options. Writing the kanji always asks
  for the kanji.
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
| The collections have fewer than 2 usable items (active, with the fields the exercise asks; for writing, kanji or words with every character's stroke order), or the exercise has no collection left | The session can't start |
| A drawing answers a choice card, an option answers a drawing, a word is written in the wrong number of boxes, or a drawing goes off the square | Rejected as invalid |
| A card is answered again, or the session has ended | Rejected; the first answer counts |
| The collection loses its usable items during a session | No more cards; the user can finish the session |

Technical details: [exercises design](../../technical/exercises.md) and
[endpoints](../../technical/api/endpoints.md#exercises).
