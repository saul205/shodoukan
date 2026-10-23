# Web Interface — Functional Guide

## Layout

The web interface (`shodoukan-web`) is a single-page dictionary lookup tool.

```
┌─────────────────────────────────────────────────┐
│  [Search input field…] [Language ▾] [Search]    │
├───────────┬─────────────────────────────────────┤
│  食       │  食べる                              │
│  eat,food │  たべる                              │
│  Kun:た.  │  ──────────────────────────────────  │
│  べる     │  JLPT N5   common                   │
│  On: ショ │  1. (v1, vt) to eat                 │
│  ク       │  2. (v1, vt) to live on              │
└───────────┴─────────────────────────────────────┘
```

- **Left column** — kanji cards, one per related character
- **Right section** — dictionary entries in ranked order

On mobile the layout stacks: entries on top, kanji cards below.

---

## Search bar

- Accepts kanji, kana, romaji, or any supported gloss language
- Pressing Enter or clicking **Search** runs the search
- The **language selector** (inside the bar) switches the definition language for both entries and kanji meanings
- On narrow screens the input wraps to its own row; the language selector and button center on the next row

---

## Entry cards

Each card shows one dictionary entry:

| Element | Description |
|---|---|
| Primary form | Kanji writing, or kana if no kanji form |
| Reading | Kana pronunciation (shown above the primary form) |
| JLPT badge | N1–N5 level, indigo colour |
| Common badge | Teal badge for high-frequency words |
| Sense list | Numbered definitions with part-of-speech tags |
| Notes | Italicised notes for usage restrictions, dialect, etc. |

---

## Kanji cards

Each card (left column) covers one character:

| Element | Description |
|---|---|
| Character | Large Japanese font |
| Meanings | Comma-separated, in the selected language |
| Kun-readings | Native Japanese readings |
| On-readings | Chinese-derived readings |
| JLPT badge | Level badge if the character is in the JLPT list |

---

## Kanji page

Opening a kanji (`/kanji/{literal}`) shows its data and readings, how to write it, and
the words that use it. The stroke order is in Japanese order and comes from
[KanjiVG](https://kanjivg.tagaini.net/), credited on the About page:

- **Diagram:** the whole character with each stroke numbered.
- **Animated:** Play draws the strokes one at a time. With reduced motion turned on in
  the system, they appear at once.
- **Stroke by stroke:** one frame per stroke. The new stroke is highlighted, and a red
  dot marks where it starts.

All jōyō kanji have stroke order, about 6,400 kanji in total. For the rare ones without
it, the frames say "Stroke order not available." and the diagram and animation stay
empty.

---

## About page

`/about` says what shodoukan is, then credits every data source, with its author, a
link and its licence:

- JMdict, KANJIDIC2 and RADKFILE (EDRDG)
- KanjiVG
- Tatoeba and the Tanaka Corpus
- the JLPT lists

It names Jisho as the inspiration, and ends with the repositories and the tech stack.
This is where the sources are credited, not next to each item. The old `/sources`
page redirects here.

---

## Debug mode

When the API runs with `SHODOUKAN_DEBUG=1`, each entry card shows a debug bar at the bottom with the internal ranking scores used to order results:

- `sort` — the effective sort key (highlighted in amber)
- `freq`, `jlpt_bonus`, `exact_match` — for Japanese searches
- `fts_rank`, `composite`, `sense_pos`, `total_senses` — for gloss searches

This is intended for development and ranking tuning, not for end users.
