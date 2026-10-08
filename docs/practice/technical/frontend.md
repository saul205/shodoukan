# Frontend (`shodoukan-practice-web`)

[← Technical documentation](README.md)

The practice app's web interface. Code: `packages/shodoukan-practice-web/`. It talks
only to the practice API (never to `shodoukan-api`) and reuses the dictionary's cards
from [`shodoukan-ui`](../../technical/frontend.md#components).

## Stack

| | |
|---|---|
| Framework | **Nuxt 4** (Vue 3, Composition API), `app/` source directory |
| UI | **Nuxt UI 4** (Tailwind CSS 4), colours `primary: indigo`, `neutral: zinc`, dark by default; conventions in the `nuxt-ui` skill (`.claude/skills/nuxt-ui/`) |
| Shared components | `shodoukan-ui` (workspace package): `EntryCard`, `KanjiCardCompact`, `KanjiStrokeAnimator`, `KanjiStrokeGrid` (through `KanjiStrokeOrder`), dictionary models |
| Sign-in | `oidc-client-ts` (OpenID Connect, authorization code + PKCE) |
| Forms | `UForm` + Zod schemas |
| Tests | Vitest, Vue Test Utils, `@nuxt/test-utils` |

It's a **client-only SPA** (`ssr: false`) on port **3001**. Why Nuxt 4 and no SSR:
[decisions](decisions.md#the-practice-frontend-is-a-nuxt-4-spa-with-nuxt-ui).

`shodoukan-ui`'s stylesheet is imported in `app/assets/css/main.css` into
`@layer components`, not through `css` in `nuxt.config.ts`. The library is built with
Tailwind 3, whose utilities aren't in a cascade layer, and unlayered CSS beats every
layer: its `.px-3` overrode Nuxt UI's `ps-*`, so input icons covered the text. In
`components` it still beats Tailwind's reset but this app's utilities win.

## Running

```bash
pnpm install
pnpm --filter shodoukan-ui build                 # the app imports the library's build
pnpm --filter shodoukan-practice-web dev         # http://localhost:3001
pnpm --filter shodoukan-practice-web test
pnpm --filter shodoukan-practice-web typecheck
```

The workspace pins **pnpm 11** (`packageManager` in the root `package.json`; CI reads
it too). pnpm 11 refuses packages published less than a day ago
(`minimumReleaseAge`): if an install fails on a fresh release, use the previous
version until it's a day old rather than relaxing the policy. Install scripts are off
(`allowBuilds` in `pnpm-workspace.yaml`); approve one there only if it's needed.

It needs the practice API on `:8001` and Keycloak on `:8080` (see
[configuration](cross-cutting/configuration.md)). Defaults are in `nuxt.config.ts`
(`runtimeConfig.public`) and can be overridden with environment variables:

| Variable | Default |
|---|---|
| `NUXT_PUBLIC_API_BASE` | `http://localhost:8001` |
| `NUXT_PUBLIC_AUTH_ISSUER` | `http://localhost:8080/realms/shodoukan` |
| `NUXT_PUBLIC_AUTH_CLIENT_ID` | `shodoukan-practice-web` |

Deployed, the app is generated as static files (`nuxt generate`) and served by Caddy at
the site root (`deploy/web/Dockerfile`, [deployment](../../technical/deployment.md)). The
build sets same-host paths, `NUXT_PUBLIC_API_BASE=/practice-api` and
`NUXT_PUBLIC_AUTH_ISSUER=/idp/realms/shodoukan`, so one build works on any host. The
auth plugin resolves a relative issuer against the page's origin (`resolveAuthority`
in `app/utils/auth-authority.ts`), because `oidc-client-ts` needs an absolute
authority.

## Sign-in

Every screen requires sign-in; only `/auth/callback` is public.

1. `plugins/01.auth.client.ts` creates the `UserManager` (`oidc-client-ts`) for the
   Keycloak client `shodoukan-practice-web` ([authentication](api/authentication.md)):
   redirect `/auth/callback`, scope `openid profile`, tokens in **sessionStorage**,
   `automaticSilentRenew` with the refresh token (access tokens last 5 minutes).
2. `middleware/auth.global.ts` asks `useAuth().accessToken()` for a valid token
   (renewing an expired one). Without one it calls `login(to.fullPath)`, which redirects
   to Keycloak with the target path in the OIDC `state`, and aborts the navigation.
3. Keycloak sends the user to `/auth/callback`; `completeLogin()` exchanges the code
   and the page navigates to the saved path. `utils/return-path.ts` only accepts paths
   inside the app, so the state can't redirect off-site.
4. Logging out (`useAuth().logout()`) ends the Keycloak session and returns to `/`.

## Talking to the API

- `utils/api-client.ts` `createApiClient()`: `$fetch` with the API base URL, the bearer
  token on every request, and sign-in again on a `401`. `plugins/02.api.client.ts`
  provides it; components get it with `useApi()`.
- `services/{dictionary,library,collections}.ts`: one typed function per endpoint,
  taking the client as first argument. Practice models are in `models/practice.ts`;
  dictionary results reuse `shodoukan-ui`'s models.
- Library edits replace the item with the API's response
  (`composables/useEditableItem.ts`), so there's no client-side merging.
- Errors become toasts (`useNotify()`); a `409` on a collection name is shown on the
  form field.

## Screens

The default layout is Nuxt UI's dashboard: `UDashboardGroup` with a collapsible
`UDashboardSidebar` (state kept in localStorage; a slideover on mobile). The sidebar
has the six sections, the **meaning language** (`useMeaningLang()`, kept in
localStorage), an "Acerca de" link to `/about` and the user menu. Every page uses `AppPanel` (navbar with the collapse
button, title and actions).

| Route | Screen |
|---|---|
| `/` | Home: the six sections |
| `/dictionary?q=&page=` | Search; `shodoukan-ui` cards with an icon-only split button over each card's corner (beside the card's link, not inside it): `ImportButton` (import, or remove on hover/focus with `ConfirmModal`) and `CollectionMenuButton` (see below), in a `UFieldGroup`; status from `GET /library/imported` (`useImportStatus()`) |
| `/dictionary/entries/:id`, `/dictionary/kanji/:literal` | Dictionary details (senses, examples, kanji; readings, stroke order (`KanjiStrokeOrder`), words using the kanji; the kanji's meanings are large and fill its height, with its data at the base), with the split button (labelled `ImportButton`) and, once imported, a link to the library copy; top right; on phones they take their own centred row below the headword (wrapping on very narrow screens), so the meanings keep the width. The entry page's kanji are `EntryKanjiList`: the cards with the corner split button, plus "import the missing ones" (`addKanjiList`, one notification) |
| `/library?tab=&q=&active=&page=` | The library: words / kanji tabs, search (`LibrarySearchInput`: updates 300 ms after typing stops, at once on Enter or clear; `meaning_lang` is `glossCode` for words and `lang` for kanji; kept when switching tab), active filter (`useActiveFilter()`, shared with collections), paging |
| `/library/entries/new?collection=` | **Nueva palabra** (from the library's header, and "Nueva palabra propia" in a word collection's menu, which passes `collection`): spellings and readings typed in one box each (`splitForms`: commas, 、 or spaces), readings checked as kana (`isKana`), the first meaning in the chosen language; `createOwnEntry` (`POST /library/entries/own`, with the collection) and then the word's page. 400 ms after typing, the first spelling (else reading) is looked up in the dictionary search and exact matches are shown in an alert linking to the dictionary, to import instead |
| `/library/entries/:id`, `/library/kanji/:id` | **Shared detail page** for the library and collections: the main column is `EntryDetail` / `KanjiDetail` (presentational: they emit the edits and the page saves them; `view-only` shows only what's enabled, without controls, for the item detail opened from a session), only the senses with a meaning in the chosen language (`sensesIn`); a switch per sense (a disabled one is faded, "oculto al practicar"; view-only leaves it out, and `entryMeanings` skips it everywhere), own senses marked "propio" with a delete button (the page confirms: its meanings, examples and note go too) and a "Nuevo significado" form under the senses that creates one with its first meaning in the chosen language; `MeaningList` (dictionary meanings only toggle; own meanings add / edit / delete), switches for examples, `FormList` for spellings and for readings (each switched; the user's own, "propio", deleted; a box adds one, kana only for readings; a word of the user's own is marked "palabra propia", has no dictionary link, lists its first spelling's kanji from `/dictionary/kanji/{literal}` and warns that removing it loses it) (a kanji's readings are `ReadingChips`: chips that toggle on click, hidden ones faded and struck through), `NotesEditor` (general and per sense, saved on blur), active, `ItemCollections` (the "Colecciones" section: removable badges and a `CollectionPicker` in its header), removal. The entry page lists the word's kanji after the meanings with the dictionary's `EntryKanjiList` (`GET /dictionary/entries/{source_entry_id}/kanji`, `link-to="library"`: imported kanji open the library copy). The kanji page puts its data under the kanji, the readings beside it and the stroke order (`KanjiStrokeOrder`: animation at 128 px + frames at `4.5rem`) below, then the meanings; its aside ends with `KanjiWords`: the first 5 dictionary words with the kanji (imported ones open the library copy, via `useImportStatus`) and a link to search the dictionary for the kanji (`/dictionary?q=`; like Jisho, it matches words *starting* with it; a "contains" filter is left for the search filters) |
| `/collections?tab=` | Collections of words / kanji: create and edit (`CollectionFormModal`), delete (`ConfirmModal`) |
| `/practice?kind=&collection=` | "Practicar escritura": tabs for Kanji, Palabras and Kana (`?kind=entries` opens Palabras). Kanji and words: collections of that kind (preselected with `?collection=`) or the whole library; kana: rows of `KANA_ROWS` (`utils/kana.ts`, checkbox cards, "Todas" per script). Then the mode (a card `URadioGroup`), the free repetitions and shuffle. Empezar loads every page of active items (`limit=100`, the API's largest), dedupes by id (dropping words with nothing to write), and opens `/practice/play` with their ids. Linked from the sidebar and from a collection's header |
| `/practice/play?kanji=\|entries=\|chars=&mode=&reps=&from=` | Writing practice (below) of library kanji or words by id (`kanji=12,15`, `entries=3,4`; `parseIds` / `formatIds`), so their own meanings show, or of bare characters (`chars=`: kana, or a kanji linked without an id). Any page can link to it; the mode select updates `mode`. `from` (a path, `safeReturnPath`) is where the back button and Volver go, `/practice` by default. Linked from a library kanji ("Practicar") and a library word ("Practicar escritura") |
| `/exercises` | The user's exercises as cards: item kind, "Escribir a mano" for handwriting ones, collections (by name; "Sin colecciones" when they were all deleted) and directions; the name opens the exercise; Empezar, edit, delete (`ConfirmModal`; past sessions are kept). `OpenSessionAlert` on top (also on the home page): "Continuar" for the open session |
| `/exercises/:id?page=` | One exercise: its definition (kind, collections, type, directions, back, and options for a choice card), "Empezar" or, if the open session is this exercise's, "Continuar", "Editar", its **statistics** once it has answers (`GET /exercises/{id}/statistics`: `TotalsTiles`, accuracy per direction as `AccuracyBar`s, the items missed most as `MissedItems`, which open `ItemDetailModal`), and its session history: a `UTable` of `GET /exercise-sessions?exercise_id=` (10 per page, `UPagination`; date, duration, answered, accuracy, open or finished) whose rows open the session |
| `/statistics?days=&tab=` | "Estadísticas": `GET /statistics` with `days` (7, 30 by default, or 90; a select) and `tz`, this browser's time zone (`Intl.DateTimeFormat().resolvedOptions().timeZone`). `TotalsTiles`, the activity of each day as an `ActivityChart` (CSS bars, right answers under wrong ones, scaled to the busiest day; a text summary for screen readers), a `UTable` per exercise (sessions, accuracy, last time; a row opens the exercise) and the words / kanji missed most in tabs (`tab=kanji`). An empty state when nothing was answered yet. No chart library |
| `/about` | "Acerca de": the shared `AboutSources` (`lang="es"`) in an `AppPanel`. It says what shodoukan is and credits every data source with its licence, and Jisho as inspiration. Sources are credited only here, not next to the data |
| `/exercise-sessions/:id?filter=` | Play a session (below). A finished one shows its result (answered, right, accuracy, date, duration) with "Practicar otra vez", then the **review**: each answered question collapsed to one line (`ReviewQuestion`, a `UCollapsible`: number, verdict, prompt → right answer, the wrong pick struck through or, for a drawing, a thumbnail of it; the time) that opens to the card as it was played (the compact `StudyCard`, its back only, and `ChoiceOptions` with the pick and the right one marked, or the drawing's `StrokeComparison`). A drawing graded "close" has the badge "Mejorable" (`utils/verdict.ts`), "Desplegar todas" / "Plegar todas", all or only the missed and skipped (`filter=missed`). The back button goes to the exercise, or to the list if it was deleted |
| `/exercises/new`, `/exercises/:id/edit` | `ExerciseForm` (below) in a card; saving goes back to the list |
| `/collections/:kind/:id?q=&active=&page=` | A collection's items with search (`LibrarySearchInput`, `in_collection` on the API side), the same active filter as the library (inactive ones are listed, marked, unless filtered out) and paging; add from the library (`LibraryPickerModal`: its own search, `not_in_collection` so only what can still be added is listed, selection kept across searches), remove; items open the detail page with `?collection=<id>` for the back link (`useBackLink()`) |

**Stroke order.** `KanjiStrokeOrder` (`literal`, `size`, `cellSize`) is used by both
kanji screens:

- **Data:** it fetches the strokes once with `GET /dictionary/kanji/{literal}/strokes`
  (`useAsyncData`, keyed by kanji). It hands them to the presentational
  `KanjiStrokeAnimator` and `KanjiStrokeGrid` from `shodoukan-ui`.
- **No drawing:** a `404` means there's no drawing. The frames then say "Orden de
  trazos no disponible." and Play is disabled.
- **Attribution:** none here. KanjiVG is credited once, on `/about`.
- **Placement:** `KanjiDetail` stays presentational, because the fetch lives in this
  component.

The data is KanjiVG (Japanese stroke order), not hanzi-writer:
[decisions](decisions.md#stroke-order-comes-from-kanjivg-without-a-hanzi-writer-fallback).

**Adding to a collection** (`CollectionPicker`): one picker for the dictionary and the
library, an icon-only `USelectMenu` with a search where typing a new name offers
«Crear "…"» (`create-item`). It's presentational: it emits `open`, `add`, `remove` and
`create`, and the caller does the requests with `useItemCollections(kind, itemId)`
(`load`, `add`, `remove`, `create`). Its `color` and `variant` make it look like a
`UButton` (a select's own `color` only tints the focus ring, and it has no `solid`), so
in the dictionary it matches the import button beside it. It has two modes
([decisions](decisions.md#one-collection-picker-two-modes)):

- **Library** (default), in the header of `ItemCollections`: only the collections the
  item isn't in, because the section already lists the others with their remove
  buttons. Creating adds the item to the new collection.
- **Dictionary** (`show-selected`), wrapped by `CollectionMenuButton`, the folder half of
  the split button: every collection, ticked where the item is (`multiple`), so it can be
  taken out. They load when the menu opens, not once per result. For an item that isn't
  imported yet, picking or creating a collection emits `import` and the page calls
  `useImportStatus().addEntry(id, collection)` (or `addKanji`), a single
  `POST /library/...` with `collection_ids`, so the import and the collection never get
  out of step ([decisions](decisions.md#importing-into-collections-is-one-request)).

**Exercise form** (`ExerciseForm`): name, description, item kind (a radio group,
fixed when editing), the exercise type ("Elegir entre opciones" / "Escribir a mano",
for both kinds), collections (a multiple `USelectMenu` of that kind's collections,
with a link to create one when there are none), directions (`DirectionsEditor`), back
fields (checkboxes) and the number of options (`UInputNumber`, 2–8; not for
drawing). A handwriting exercise passes `HANDWRITING_ANSWERS[kind]` as
`answer-fields` to the `DirectionsEditor` (the kanji; a word's writing or reading), so
every direction asks for something to write; switching the type starts the directions
and back fields over (`defaultHandwritingSettings(kind)`: meaning → kanji with the
readings on the back, or meaning → writing with the reading). Fields, their
Spanish labels and each kind's defaults are in `utils/study-fields.ts`, mirroring the
backend's `ENTRY_FIELDS` / `KANJI_FIELDS`. Switching the item kind starts collections,
directions and back fields over. The Zod schema repeats the backend's rules (at least
one collection and one direction, no direction asking a field it shows, no repeated
direction in any order of its shown fields), so mistakes show on their field; a 404 on
save (a collection deleted meanwhile) is shown on the collections field and reloads
them. The form saves on its own and emits `saved`, so the new and edit pages only
navigate. `DirectionsEditor` is one row per direction, a multiple `USelectMenu` of the
shown fields → a `USelect` of the asked field; the asked field is never offered among
the shown ones, and picking it as the answer takes it out of the prompt.

**Starting and resuming** (`composables/useExerciseSessions.ts`): `useStartExercise()`
starts a session with the meaning language as the exercise's items store it
(`useMeaningLang().codeFor(kind)`: `glossCode` for words, `lang` for kanji) and goes to
it. Starting closes the open session, so if there is one (`GET /exercise-sessions?status=open&limit=1`)
the user confirms first; a 422 (too few usable items) is a toast. `useOpenSession()`
reads the open session for `OpenSessionAlert`.

**Playing a session** (`pages/exercise-sessions/[id].vue`): the page owns the requests
and the state: the question on screen (the active one, or the one just answered with
its solution) and `next`, which the answer already brought, shown on "Siguiente". The
player for the question's `type` comes from the registry in
`components/exercise-players/index.ts` (`card.choice` → `ChoiceCardPlayer`,
`card.handwriting` → `HandwritingPlayer`, `card.handwriting_word` →
`WordHandwritingPlayer`); a player
takes `question` and `busy` and emits `answer(answer, responseMs)`, `next` and
`open-item(itemId)`. `ChoiceCardPlayer` is a `StudyCard` (front: the prompt fields with
their labels and what's asked; once answered it turns to the back, composed from the
question's `back`: the prompt fields as the headline, the asked field in green, the
other back fields smaller, and "Ver detalle") over `ChoiceOptions` (keys 1–N, then the right option green and a wrong pick
red, with "detail" buttons on options that came from an item); Enter goes on.
"Saltar" (or S / Escape) answers `{type: "skip"}`: a miss, shown with only the right
option marked and the verdict "Saltada". The shortcuts are a window `keydown` listener that
stands aside for keys with Ctrl/Cmd/Alt, for inputs, dialogs and open menus or select
lists, and lets a focused control ("Terminar", a link, a detail button) keep its
Enter: Enter means "next" only from the page itself or an option
(`data-option-shortcuts`). It
measures `response_ms` from when the question is shown. The layout stays put: the page uses
`AppPanel fill` (the content stretches to the panel's height), and in the player the
options and a bottom row (a key hint, then the verdict and "Siguiente") take their
height while the card takes the rest. The card shows one face at a time (front, then
the back after a short flip). Its minimum height, from the front on, is the back's
estimated height: the page loads the exercise (`getExercise`) for its `back_fields`
and passes them to the player as `backFields`, and `StudyCard` adds up the rows the
back will have (prompt fields, answer, extras) at phone line heights, so turning
doesn't resize it. A back longer than estimated (values that wrap) grows the card
and shrinks the options to their minimum; it doesn't scroll inside the card. The
options are rows of equal height (`auto-rows-fr`, long
texts cut at three lines) with their detail buttons in a corner, so answering or going
on resizes nothing. The goal is that a session never scrolls on a phone: there the card
and the options share the height 2:3 (`flex-[2_1_0%]` / `flex-[3_1_0%]`, neither
below its content), so the options grow into the room the card doesn't need, and
they go in one column, two when the texts are short (≤ 6 characters for a Japanese
answer, 12 otherwise) or when one column wouldn't fit (7–8 options, or 5–6 on a
screen under 40rem tall). From `sm` the card takes the rest. Text grows with the
screen. `next: null` shows "No quedan
preguntas" with "Terminar"; an answer that finished the session (its exercise was
deleted) reloads it into its result; a 409 (answered in another tab, closed or idle
meanwhile) reloads the session with a toast. `ItemDetailModal` (`useOverlay()`) loads
the library item and shows `EntryDetail` / `KanjiDetail` view-only plus its notes, with
"Abrir en la librería", which goes to the item's library page in the same window with
`?from=<the opening page's path>`: its back button (`useBackLink()`, which only takes
session, exercise and statistics paths, through `safeReturnPath`) returns there: a
session picks up where it was, a review keeps its filter, an exercise or the
statistics come back as they were; which review questions
were open is kept per session in `useState`. An item no longer in the library
says so.

**Drawing the kanji** (`HandwritingPlayer`): before answering, the front is a compact
strip (`StudyCard compact`: the prompt and "¿Kanji?") and `KanjiDrawingPad` (from
`shodoukan-ui`) takes the rest of the height as the largest square that fits, so
it's comfortable on a phone and a session never scrolls, on a phone or a PC: a
drawing is capped at what the API takes (40 strokes of up to 300 points:
`maxStrokes` / `maxPoints`, with a notice at the limit), and undo and clear do nothing
while a drawing is being sent, so the strokes graded are the ones on screen. A
`ResizeObserver` measures the box it sits in, and the pad is absolutely positioned
inside it, so its own size can't grow the box (a flex child sized by its content
would, and the pad would follow). It isn't drawn until the box is measured. Below it: undo
(Backspace, Ctrl/Cmd+Z), clear, "Saltar" (S / Escape) and "Comprobar" (Enter, once
something is drawn), which sends `{type: "strokes", strokes}` in KanjiVG's space,
with no conversion. Once answered the drawing is what matters, not the card: the
verdict ("¡Correcto!", "Mejorable" with the score, "Fallada") and "Siguiente", then
`StrokeComparison` and what was wrong with each stroke ("Trazo 3: en sentido
contrario.", "Trazo 2: demasiado largo."). The card (its back) is a "Ver tarjeta" collapsible on phones and a
column beside the drawing from `lg`; "Ver detalle" there opens the item, whose kanji
page has the stroke order animation. The comparison is sized the same way, on the room the verdict row,
the stroke problems and the card leave (two squares side by side from `sm`, one on a
phone); only the card's column may scroll. `StrokeComparison` draws the drawing (each stroke
coloured by its grade: green, amber for backwards, out of order, too long or short, or
imprecise, red for extra) next to the matched KanjiVG kanji (numbered, strokes not drawn in red), both
with `KanjiStrokeDiagram`; on a phone one square shows them overlaid (the reference
as a faint `ghost`), or each in turn.

**Writing practice** (`WritingPractice`): a queue of `PracticeItem`s (a library kanji
or word by id, or a bare character), each written guided, free, or guided once and
then free `reps` times (`practiceSteps` in `utils/writing-practice.ts`, by item
index). `usePracticeItem` resolves the current item, and prefetches the next, to its
text, reading and up to three meanings in the meaning language: a library kanji's
enabled kun and on readings and `kanjiMeanings`, a word's `entryWriting` (the card's
headword and reading) and `entryMeanings`, a bare kanji's dictionary meanings (none for
kana). It keeps what it fetched only for that practice (a map per call), so a practice started later, after the item was edited or removed, shows it as it is then. A strip on top shows the item, its reading and meanings, the step
("Guiado", "Libre · 1 de 2"), the progress and the mode select (changing it restarts
the current item). An item gone from the library (404), or a lone character without
strokes, is shown as missing and "Siguiente" skips all its steps. Once written: "Otra
vez" (remounts the board) or "Siguiente" (Enter); Ctrl/Cmd+Z undoes. Nothing is sent to
the API ([decisions](decisions.md#writing-practice-is-ephemeral-and-frontend-only)).

- `WordWritingBoard`: writes the item whole, a cell per character, with one row of
  controls. `useWordStrokes` loads every character's strokes together (404 is `null`:
  that cell is shown as given). The board measures its room (`useMeasuredBox`) and
  `fitCells` picks the number of columns that makes the cells largest (a row on a PC,
  two columns on a phone held upright); under `MIN_CELL` (120 px) it shows one cell
  at a time, with a row of small cells above (and ◀ ▶ when free). Nothing scrolls,
  since the page can't scroll while drawing. Guided, only the current cell is a
  `GuidedCell`; done cells are `KanjiStrokeDiagram`s in ink, pending ones a grey
  `ghost`, and the next cell takes over by itself. Its status line shows the stroke
  or the hint, with undo, restart and "Saltar trazo" (after three misses). Free, every
  cell is a `FreeCell`, the last one touched is the one undo and clear act on, and one
  Comprobar checks them all.
- `GuidedCell`: the model in grey, the strokes done in ink and the next one animated
  in a loop (`pathLength="1"` and a dash offset; still with reduced motion) from a red
  dot at `strokeStart`, all in the pad's `background` slot. Each traced stroke is
  judged with `matchStroke` from `shodoukan-ui` and wiped from the pad: a match adds
  the model's stroke, a miss gives a hint (backwards, wrong start, or off the shape).
  It reports `progress` and `done`, and exposes undo, restart and skip.
- `FreeCell`: the pad with the model in the `background` slot when shown (the switch
  is the board's, kept across items); once checked, a `KanjiStrokeDiagram` of the
  drawing over the model as a `ghost`, with the stroke counts in a corner. No grade.
- `PracticeModal`: `WritingPractice` in a `UModal` (full screen on phones), opened
  with `useOverlay()` by `HandwritingPlayer` once answered ("Practicar kanji") and by
  `ReviewQuestion` for a drawing ("Practicar 一"), with the library kanji asked for
  (`item_id`; the literal, `references[0]`, when there is none). The session stays
  mounted underneath; its shortcuts ignore keys from inside a dialog.

**Writing a word** (`WordHandwritingPlayer`): a compact front, then a cell per
character (`question.cell_count`, the only part of the solution shown before
answering), each a `FreeCell` without a model, laid out like the practice board
(`fitCells`: a row on a PC, two columns on a phone; one cell at a time, with a row of
numbered cells and ◀ ▶, when they'd be under 120 px). Any cell can be drawn in; undo
(Backspace, Ctrl/Cmd+Z) and clear act on the last one touched; "Saltar" (S) and
"Comprobar" (Enter) send `{type: "cells", cells}`. Once answered: the verdict and
score, "Practicar palabra" (the word in `PracticeModal`, by its library id) and
"Siguiente", then `WordComparison`: each cell's drawing over its character, coloured
by its grade, with the character and its score; picking one shows its
`StrokeComparison` and what was wrong with its strokes, after "Parece ろ." when its
grade's `looks_like` says it was taken for another character. The review uses the same
component, compact, with a thumbnail per character in the summary line.

The detail is a page, not a modal: it has its own URL, the back button works, and it
has room for editing. List state (tab, filter, page, query) lives in the URL for the
same reason.

## Tests

`tests/unit/` runs in happy-dom: the API client (token, 401), the session formats (`utils/session-format.ts`), the verdicts and stroke problems (`utils/verdict.ts`), `apiStatus` (also
through `useAsyncData`'s wrapped error), `safeReturnPath`, the service functions, the practice steps, ids in the query, a word's writing and `fitCells` (`utils/writing-practice.ts`), the kana rows (`utils/kana.ts`). `tests/components/` runs in the Nuxt environment
(`// @vitest-environment nuxt`, `mountSuspended`): the sign-in middleware,
`MeaningList`, `FormList` (deleting only own forms, kana only for readings), the new word page (created in its collection, kana check, dictionary matches), the library word page (an edit doesn't fetch the word's kanji again), `EntryDetail` (sense switches, own senses removed and added, disabled senses left out view-only), `NotesEditor`, `CollectionFormModal`, `CollectionMenuButton`, `KanjiWords`, `KanjiStrokeOrder` (one fetch, 404, no per-kanji credit), the about page, `EntryKanjiList`, `ItemCollections`, `CollectionPicker`, `DirectionsEditor`, `ExerciseForm`, `ChoiceOptions`, `ChoiceCardPlayer` (keys, `response_ms`), `HandwritingPlayer` (check only once drawn, undo and clear, skip, the verdict and stroke problems once drawn, practising the kanji), `GuidedCell` (a matching stroke snaps, a miss is wiped with a hint, skip, undo and restart), `FreeCell` (hiding the model, the overlay and counts once checked), `WordWritingBoard` (a row on a PC, two columns on a phone, one cell at a time when small, one Comprobar for every cell, the next guided cell taking over, characters without strokes), `WritingPractice` (guided then free, readings and meanings of library and bare items, Otra vez, missing items, finishing), the practice page (every page of a collection's active kanji, the library, a word collection, kana rows; ids in the query), `StrokeComparison`, `ReviewQuestion` (choice, drawing and word summaries, practising a drawing's kanji or word), `WordHandwritingPlayer` (a row or two columns of cells, one at a time when small, one Comprobar for every cell, undo and clear on the cell touched, skip, the verdict and each character once written, practising the word), the statistics components and page (window and time zone, tabs, empty state), the exercise page (history, continue or start, statistics), the session page (answer, next, no more questions, 409 reload, review and its filter; `clearNuxtData()` between tests that load the same key), the view-only `MeaningList` and `ReadingChips`, the exercise edit page's not-found state (menus
and tooltips need the `UApp` wrapper; their content is portalled to the body). They replace `useAuth` with
`tests/fakes.ts` (`mockNuxtImport`), because the real middleware would redirect to
Keycloak while the test app starts.
