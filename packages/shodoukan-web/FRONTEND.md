# shodoukan-web — Frontend Reference

Nuxt 3 SPA backed by the `shodoukan-api` FastAPI service.

## Tech stack

| Layer | Tool |
|---|---|
| Framework | Nuxt 3 (Vue 3, Composition API) |
| Styling | Tailwind CSS |
| Type checking | TypeScript (strict) |
| Tests | Vitest + Vue Test Utils |

## Running locally

```bash
cd packages/shodoukan-web
npm install
npm run dev          # dev server at http://localhost:3000
npm run build        # production build
npm test             # unit tests
```

The API base URL is set via `nuxt.config.ts` (runtime config `apiBase`). By default it points to `http://localhost:8000`.

---

## Page structure

Single page: `pages/index.vue`.

```
main (80% viewport width, centred)
├── search row (max 60% width — space reserved for future logo/branding)
│   ├── SearchBar        — text input + Search button
│   └── LanguageSelector — ISO 639-1 language dropdown
└── results (flex-wrap-reverse, gap-6)
    ├── aside (kanji cards, shrink-0, flex-wrap)
    │   └── KanjiCardCompact × N
    └── section (entries, flex-1, min-w-[28rem])
        └── EntryCard × N
```

### Responsive behaviour

The results row uses `flex-wrap-reverse`. When the viewport is wide enough both the kanji `aside` and the entries `section` sit side by side (kanji on the left). When the viewport narrows below the sum of their minimum widths, the `section` wraps to a new row — and because `flex-wrap-reverse` inserts new rows *above*, entries stay on top and kanji cards fall below.

`min-w-[28rem]` on `section` sets the legibility threshold for entries. `min-content` was considered but resolves to near-zero for text, which would let entries compress unreadably before wrapping.

---

## Components

| File | Purpose |
|---|---|
| `SearchBar.vue` | Controlled text input with enter-key and button submit |
| `LanguageSelector.vue` | `<select>` bound to `SUPPORTED_LANGUAGES` from `models/kanji.ts` |
| `EntryCard.vue` | Full dictionary entry: headword, reading, JLPT/common tags, senses, optional debug bar |
| `KanjiCard.vue` | Detailed kanji view (readings, meanings, stroke count, grade) |
| `KanjiCardCompact.vue` | Compact sidebar card (`w-28` fixed width) used in the results aside |

---

## Models

### `models/entry.ts`

- `Entry` — mirrors the Python `Entry` Pydantic model. Key fields:
  - `is_common: boolean` — pre-computed on the backend from `EntryORM.has_common`; the frontend must **not** derive commonness from priority tags
  - `score: ScoreBreakdown | null` — present only when the API runs with `SHODOUKAN_DEBUG=1`
- `ScoreBreakdown` — mirrors `shodoukan.models.entry.ScoreBreakdown`

### `models/kanji.ts`

- `Kanji`, `KanjiMeaning`
- `SUPPORTED_LANGUAGES` — array of `{ code, label, glossLang }` used by `LanguageSelector`
- `glossLang(lang)` — maps ISO 639-1 codes (`en`, `es`, …) to JMDict gloss lang codes (`eng`, `spa`, …)

### `models/search.ts`

- `SearchResult` — `{ entries: Page<Entry>, kanji: Kanji[] }`

---

## Debug mode

Set `SHODOUKAN_DEBUG=1` in the API environment. Each `Entry` in the response will include a `score` object with ranking internals.

`EntryCard` renders a debug bar at the bottom of the card when `entry.score` is non-null:

- `sort: <value>` — the **effective sort key** (highlighted in amber), derived as:
  - Gloss search: `composite`
  - Japanese search: `freq + jlpt_bonus`
- Followed by all non-null individual fields: `freq`, `jlpt_bonus`, `exact_match`, `fts_rank`, `sense_pos`, `total_senses`, `composite`

---

## Tailwind conventions

- **Palette**: dark zinc background (`zinc-800`, `zinc-900`), light zinc text (`zinc-100`, `zinc-200`, `zinc-400`, `zinc-500`)
- **Accents**: indigo (`indigo-600`) for JLPT badges and interactive elements; teal (`teal-600`) for the "common" badge; amber (`amber-400`) for debug highlights
- **Typography**: `font-sans` (Inter) for UI text; `font-japanese` (Noto Sans JP) for Japanese characters
- **Cards**: `rounded-lg border border-zinc-800 bg-zinc-800/50` — shared visual treatment for all result cards
