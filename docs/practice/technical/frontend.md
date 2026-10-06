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
has the five sections, the **meaning language** (`useMeaningLang()`, kept in
localStorage), an "Acerca de" link to `/about` and the user menu. Every page uses `AppPanel` (navbar with the collapse
button, title and actions).

| Route | Screen |
|---|---|
| `/` | Home: the five sections |
| `/dictionary?q=&page=` | Search; `shodoukan-ui` cards with an icon-only split button over each card's corner (beside the card's link, not inside it): `ImportButton` (import, or remove on hover/focus with `ConfirmModal`) and `CollectionMenuButton` (see below), in a `UFieldGroup`; status from `GET /library/imported` (`useImportStatus()`) |
| `/dictionary/entries/:id`, `/dictionary/kanji/:literal` | Dictionary details (senses, examples, kanji; readings, stroke order (`KanjiStrokeOrder`), words using the kanji; the kanji's meanings are large and fill its height, with its data at the base), with the split button (labelled `ImportButton`) and, once imported, a link to the library copy; top right; on phones they take their own centred row below the headword (wrapping on very narrow screens), so the meanings keep the width. The entry page's kanji are `EntryKanjiList`: the cards with the corner split button, plus "import the missing ones" (`addKanjiList`, one notification) |
| `/library?tab=&q=&active=&page=` | The library: words / kanji tabs, search (`LibrarySearchInput`: updates 300 ms after typing stops, at once on Enter or clear; `meaning_lang` is `glossCode` for words and `lang` for kanji; kept when switching tab), active filter (`useActiveFilter()`, shared with collections), paging |
| `/library/entries/:id`, `/library/kanji/:id` | **Shared detail page** for the library and collections: the main column is `EntryDetail` / `KanjiDetail` (presentational: they emit the edits and the page saves them; `view-only` shows only what's enabled, without controls, for the item detail opened from a session), only the senses with a meaning in the chosen language (`sensesIn`); `MeaningList` (dictionary meanings only toggle; own meanings add / edit / delete), switches for spellings, readings and examples (a kanji's readings are `ReadingChips`: chips that toggle on click, hidden ones faded and struck through), `NotesEditor` (general and per sense, saved on blur), active, `ItemCollections` (the "Colecciones" section: removable badges and a `CollectionPicker` in its header), removal. The entry page lists the word's kanji after the meanings with the dictionary's `EntryKanjiList` (`GET /dictionary/entries/{source_entry_id}/kanji`, `link-to="library"`: imported kanji open the library copy). The kanji page puts its data under the kanji, the readings beside it and the stroke order (`KanjiStrokeOrder`: animation at 128 px + frames at `4.5rem`) below, then the meanings; its aside ends with `KanjiWords`: the first 5 dictionary words with the kanji (imported ones open the library copy, via `useImportStatus`) and a link to search the dictionary for the kanji (`/dictionary?q=`; like Jisho, it matches words *starting* with it; a "contains" filter is left for the search filters) |
| `/collections?tab=` | Collections of words / kanji: create and edit (`CollectionFormModal`), delete (`ConfirmModal`) |
| `/exercises` | The user's exercises as cards: item kind, collections (by name; "Sin colecciones" when they were all deleted) and directions; the name opens the exercise; Empezar, edit, delete (`ConfirmModal`; past sessions are kept). `OpenSessionAlert` on top (also on the home page): "Continuar" for the open session |
| `/exercises/:id?page=` | One exercise: its definition (kind, collections, directions, back, options), "Empezar" or, if the open session is this exercise's, "Continuar", "Editar", its **statistics** once it has answers (`GET /exercises/{id}/statistics`: `TotalsTiles`, accuracy per direction as `AccuracyBar`s, the items missed most as `MissedItems`, which open `ItemDetailModal`), and its session history: a `UTable` of `GET /exercise-sessions?exercise_id=` (10 per page, `UPagination`; date, duration, answered, accuracy, open or finished) whose rows open the session |
| `/statistics?days=&tab=` | "Estadísticas": `GET /statistics` with `days` (7, 30 by default, or 90; a select) and `tz`, this browser's time zone (`Intl.DateTimeFormat().resolvedOptions().timeZone`). `TotalsTiles`, the activity of each day as an `ActivityChart` (CSS bars, right answers under wrong ones, scaled to the busiest day; a text summary for screen readers), a `UTable` per exercise (sessions, accuracy, last time; a row opens the exercise) and the words / kanji missed most in tabs (`tab=kanji`). An empty state when nothing was answered yet. No chart library |
| `/about` | "Acerca de": the shared `AboutSources` (`lang="es"`) in an `AppPanel`. It says what shodoukan is and credits every data source with its licence, and Jisho as inspiration. Sources are credited only here, not next to the data |
| `/exercise-sessions/:id?filter=` | Play a session (below). A finished one shows its result (answered, right, accuracy, date, duration) with "Practicar otra vez", then the **review**: each answered question collapsed to one line (`ReviewQuestion`, a `UCollapsible`: number, verdict, prompt → right answer, the wrong pick struck through, the time) that opens to the card as it was played (the compact `StudyCard`, its back only, and `ChoiceOptions` with the pick and the right one marked), "Desplegar todas" / "Plegar todas", all or only the missed and skipped (`filter=missed`). The back button goes to the exercise, or to the list if it was deleted |
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
fixed when editing), collections (a multiple `USelectMenu` of that kind's collections,
with a link to create one when there are none), directions (`DirectionsEditor`), back
fields (checkboxes) and the number of options (`UInputNumber`, 2–8). Fields, their
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
`components/exercise-players/index.ts` (`card.choice` → `ChoiceCardPlayer`); a player
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

The detail is a page, not a modal: it has its own URL, the back button works, and it
has room for editing. List state (tab, filter, page, query) lives in the URL for the
same reason.

## Tests

`tests/unit/` runs in happy-dom: the API client (token, 401), the session formats (`utils/session-format.ts`), `apiStatus` (also
through `useAsyncData`'s wrapped error), `safeReturnPath`, the service functions. `tests/components/` runs in the Nuxt environment
(`// @vitest-environment nuxt`, `mountSuspended`): the sign-in middleware,
`MeaningList`, `NotesEditor`, `CollectionFormModal`, `CollectionMenuButton`, `KanjiWords`, `KanjiStrokeOrder` (one fetch, 404, no per-kanji credit), the about page, `EntryKanjiList`, `ItemCollections`, `CollectionPicker`, `DirectionsEditor`, `ExerciseForm`, `ChoiceOptions`, `ChoiceCardPlayer` (keys, `response_ms`), the statistics components and page (window and time zone, tabs, empty state), the exercise page (history, continue or start, statistics), the session page (answer, next, no more questions, 409 reload, review and its filter; `clearNuxtData()` between tests that load the same key), the view-only `MeaningList` and `ReadingChips`, the exercise edit page's not-found state (menus
and tooltips need the `UApp` wrapper; their content is portalled to the body). They replace `useAuth` with
`tests/fakes.ts` (`mockNuxtImport`), because the real middleware would redirect to
Keycloak while the test app starts.
