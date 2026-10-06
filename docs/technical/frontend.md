# shodoukan-web — Technical Reference

Nuxt 3 SPA (`ssr: false`) backed by the `shodoukan-api` FastAPI service, published as
static files on a Render Static Site ([deployment](deployment.md#dictionary-web-static-site)).
Pages load their data in the browser after navigation, so server rendering only ever
produced a "loading" page; the static build needs no Node server.

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
npm run generate     # static build in .output/public (what gets deployed)
npm test             # unit tests
```

The API base URL is set via `nuxt.config.ts` (runtime config `apiBase`). By default it points to `http://localhost:8000`.
In the static build it's fixed at build time: set `NUXT_PUBLIC_API_BASE` when running
`generate`. The host must rewrite unknown paths to `/index.html` so routes like
`/entry/123` load on refresh.

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

The shared components, models and services live in the **`shodoukan-ui`** library
(`packages/shodoukan-ui`, a pnpm workspace package built with Vite in library mode;
build it before running an app: `pnpm --filter shodoukan-ui build`). They're shared with
the practice frontend (`shodoukan-practice-web`), so they take their link targets and
labels as props. `NavBar` and `PageContainer` stay in `shodoukan-web`.

| Component (`shodoukan-ui`) | Purpose |
|---|---|
| `SearchBar.vue` | Controlled input + language selector + submit button. Props: `modelValue` (query), `lang`. Emits: `update:modelValue`, `update:lang`, `search`. Uses `LanguageSelector` internally. |
| `LanguageSelector.vue` | `<select>` bound to `SUPPORTED_LANGUAGES` from `models/kanji.ts`. Used inside `SearchBar`. |
| `EntryCard.vue` | Full dictionary entry: headword, reading, JLPT/common tags, senses, optional debug bar. Props: `entry`, `lang`, `linkComponent` (`'a'` or e.g. `NuxtLink`), `detailsHref` (default `/entry/{id}`), `detailsLabel`. |
| `KanjiCard.vue` | Detailed kanji view (readings, meanings, stroke count, grade). |
| `KanjiCardCompact.vue` | Compact card (`min-w-[14rem] flex-1`) used in the results kanji column. Props: `kanji`, `lang`, `linkComponent`, `href` (default `/kanji/{literal}`). |
| `KanjiStrokeAnimator.vue` | Animated stroke order. Props: `strokes`, `size` (drawing size in px, default 160), and the labels `playLabel` and `playingLabel`. Shows the outline; Play draws each stroke in turn. With `prefers-reduced-motion` it draws them at once. Disabled without strokes. |
| `KanjiStrokeGrid.vue` | One frame per stroke: the strokes so far, the current one highlighted and a dot where it starts. Props: `strokes`, `loading`, `cellSize` and the labels `loadingLabel` and `unavailableLabel`. `cellSize` is the smallest frame width as a CSS length (default `6rem`), and frames grow up to twice it. Sizes are inline styles, since Tailwind 3 can't build classes from a prop. |
| `KanjiStrokeDiagram.vue` | The whole character with each stroke's number. Props: `strokes`, `size` (px, default 160, or any CSS length such as `'100%'`), `colors` (a CSS colour per stroke), `ghost` (strokes drawn faintly underneath, to overlay a reference) and `numbers` (default `true`). Drawn strokes render with it too, through `pointsToPath`. |
| `KanjiDrawingPad.vue` | A square to draw a kanji in (finger, pen or mouse), in KanjiVG's space (the 109 square plus the `KANJIVG_PADDING` margin), so drawings and references overlay as they are. `v-model` is the strokes, each a list of `[x, y]` points, simplified when the pointer lifts (`simplifyStroke`); emits `stroke-end`; exposes `undo()` and `clear()`; `disabled`. Only the primary pointer draws, and `touch-action: none` keeps the page still. |
| `AboutSources.vue` | What shodoukan is, every data source with its author, link and licence, and Jisho as inspiration. Prop `lang` (`'en'` default, or `'es'`). It's the one place sources are credited: both apps link to it, and a new data source is added here. |

The three stroke components are presentational. They take `strokes: KanjiStroke[] | null`
(`null` = no drawing), which each app fetches from its own API, and render plain SVG.
They work with server-side rendering, so `<ClientOnly>` isn't needed. The data is
KanjiVG, with Japanese stroke order, from `GET /kanji/{literal}/strokes`.

- **Coordinates:** strokes are centre lines in a 109 × 109 box (`KANJIVG_SIZE`), drawn
  unfilled with a round stroke `KANJIVG_STROKE_WIDTH` wide.
- **Animation:** each path gets `pathLength="1"`, so a dash of 1 animated from offset 1
  to 0 draws it. No length measuring is needed, and that keeps it testable in jsdom.
- **Why not hanzi-writer:** see
  [decisions](../practice/technical/decisions.md#stroke-order-comes-from-kanjivg-without-a-hanzi-writer-fallback).

### EntryCard internal layout

Tags and senses share a `flex flex-wrap` row:
- **Tags div** — `flex flex-1 flex-wrap gap-1`: with `flex-1` vs `[flex:100]` on senses, the tags div is compressed to near-zero width, forcing badges into a column. When tags wrap to their own row they expand and badges flow horizontally.
- **Senses ol** — `[flex:100] min-w-fit`: takes virtually all available width (100× the tags grow factor); `min-w-fit` establishes the minimum width before wrapping to a new row.

---

## Models

### `models/entry.ts`

- `Entry` — mirrors the Python `Entry` Pydantic model. Key fields:
  - `is_common: boolean` — pre-computed on the backend from `EntryORM.has_common`. **Do not re-derive from priority tags.**
  - `score?: ScoreBreakdown | null` — present only when the API runs with `SHODOUKAN_DEBUG=1`
  - Nested `id`s, `priority` tags and example provenance are optional: `shodoukan-api`
    sends them, the practice API's dictionary read models don't. Components key by
    index when there's no id.
- `ScoreBreakdown` — mirrors `shodoukan.models.entry.ScoreBreakdown`

### `models/kanji.ts`

- `Kanji`, `KanjiMeaning`
- `KanjiStrokes` (`literal`, `strokes`), `KanjiStroke` (`path`, `label: [x, y] | null`): the stroke order, as `GET /kanji/{literal}/strokes` returns it
- `SUPPORTED_LANGUAGES` — array of `{ code, label, glossLang }` consumed by `LanguageSelector`
- `glossLang(lang)` — maps ISO 639-1 codes (`en`, `es`, …) to JMDict gloss lang codes (`eng`, `spa`, …)

### `utils/strokes.ts`

- `KANJIVG_SIZE` (109), `KANJIVG_STROKE_WIDTH` (3)
- `strokeStart(path)`: the stroke's starting point, which the grid marks

### `models/search.ts`

- `SearchResult` — `{ entries: Page<Entry>, kanji: Kanji[] }`

---

## Debug mode

Set `SHODOUKAN_DEBUG=1` in the API environment. Each `Entry` in the response will include a `score` object with ranking internals.

`EntryCard` renders a debug bar at the bottom when `entry.score` is non-null:

- `sort: <value>` — the **effective sort key** (highlighted in amber): the API's
  `score` (`match_tier × 2000 + popularity`, see [search architecture](search.md#entry-search)).
  With an older API that doesn't send `score` it falls back to `composite` (gloss) or
  `freq + jlpt_bonus` (Japanese).
- Followed by all non-null individual fields: `tier`, `relevance`, `freq`, `jlpt_bonus`, `exact_match`, `fts_rank`, `sense_pos`, `total_senses`, `composite`

---

## Tailwind conventions

- **Palette**: dark zinc background (`zinc-800`, `zinc-900`), light zinc text (`zinc-100`, `zinc-200`, `zinc-400`, `zinc-500`)
- **Accents**: indigo (`indigo-600`) for JLPT badges and interactive elements; teal (`teal-600`) for the "common" badge; amber (`amber-400`) for debug highlights
- **Typography**: `font-sans` (Inter) for UI text; `font-japanese` (Noto Sans JP) for Japanese characters
- **Cards**: `rounded-lg border border-zinc-800 bg-zinc-800/50` — shared visual treatment for all result cards
- **Arbitrary flex values**: `[flex:0]` on the kanji column container, `[flex:100]` on the senses list — both are intentional flex-ratio tricks, not bugs
