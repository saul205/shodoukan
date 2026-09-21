# shodoukan-web — Technical Reference

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
main (w-[80%] viewport width, centred)
├── search wrapper (max-w-full on mobile, md:max-w-[60%] on desktop — reserves space for future branding)
│   └── SearchBar  — input + LanguageSelector + Search button (all internal)
└── results (flex-col-reverse on mobile, md:flex-row on desktop)
    ├── div (kanji cards, [flex:0] self-start, flex-wrap)
    │   └── KanjiCardCompact × N  (min-w-[14rem] flex-1, expand to fill row)
    └── section (entries, flex-1)
        └── EntryCard × N
```

### Responsive behaviour

- **Mobile (< md / 768px)**: `flex-col-reverse` — entries on top, kanji cards below. Search bar is full width; on very narrow screens the input wraps to its own row and the language selector + button center on the next row.
- **Desktop (≥ md)**: `flex-row` — kanji column on the left (`[flex:0]`, content-sized, does not steal space from entries), entries section on the right (`flex-1`).
- **Kanji cards** use `min-w-[14rem] flex-1` within their `flex-wrap` container: they stack in a column on desktop (container is narrow) and form a row/grid on wider viewports.

---

## Components

| File | Purpose |
|---|---|
| `SearchBar.vue` | Controlled input + language selector + submit button. Props: `modelValue` (query), `lang`. Emits: `update:modelValue`, `update:lang`, `search`. Uses `LanguageSelector` internally. |
| `LanguageSelector.vue` | `<select>` bound to `SUPPORTED_LANGUAGES` from `models/kanji.ts`. Used inside `SearchBar`. |
| `EntryCard.vue` | Full dictionary entry: headword, reading, JLPT/common tags, senses, optional debug bar. |
| `KanjiCard.vue` | Detailed kanji view (readings, meanings, stroke count, grade). |
| `KanjiCardCompact.vue` | Compact card (`min-w-[14rem] flex-1`) used in the results kanji column. |

### EntryCard internal layout

Tags and senses share a `flex flex-wrap` row:
- **Tags div** — `flex flex-1 flex-wrap gap-1`: with `flex-1` vs `[flex:100]` on senses, the tags div is compressed to near-zero width, forcing badges into a column. When tags wrap to their own row they expand and badges flow horizontally.
- **Senses ol** — `[flex:100] min-w-fit`: takes virtually all available width (100× the tags grow factor); `min-w-fit` establishes the minimum width before wrapping to a new row.

---

## Models

### `models/entry.ts`

- `Entry` — mirrors the Python `Entry` Pydantic model. Key fields:
  - `is_common: boolean` — pre-computed on the backend from `EntryORM.has_common`. **Do not re-derive from priority tags.**
  - `score: ScoreBreakdown | null` — present only when the API runs with `SHODOUKAN_DEBUG=1`
- `ScoreBreakdown` — mirrors `shodoukan.models.entry.ScoreBreakdown`

### `models/kanji.ts`

- `Kanji`, `KanjiMeaning`
- `SUPPORTED_LANGUAGES` — array of `{ code, label, glossLang }` consumed by `LanguageSelector`
- `glossLang(lang)` — maps ISO 639-1 codes (`en`, `es`, …) to JMDict gloss lang codes (`eng`, `spa`, …)

### `models/search.ts`

- `SearchResult` — `{ entries: Page<Entry>, kanji: Kanji[] }`

---

## Debug mode

Set `SHODOUKAN_DEBUG=1` in the API environment. Each `Entry` in the response will include a `score` object with ranking internals.

`EntryCard` renders a debug bar at the bottom when `entry.score` is non-null:

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
- **Arbitrary flex values**: `[flex:0]` on the kanji column container, `[flex:100]` on the senses list — both are intentional flex-ratio tricks, not bugs
