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
| Shared components | `shodoukan-ui` (workspace package): `EntryCard`, `KanjiCardCompact`, `KanjiStrokeAnimator`, `KanjiStrokeGrid`, dictionary models |
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
has the three sections, the **meaning language** (`useMeaningLang()`, kept in
localStorage) and the user menu. Every page uses `AppPanel` (navbar with the collapse
button, title and actions).

| Route | Screen |
|---|---|
| `/` | Home: the three sections |
| `/dictionary?q=&page=` | Search; `shodoukan-ui` cards, import buttons with the status from `GET /library/imported` (`useImportStatus()`) |
| `/dictionary/entries/:id`, `/dictionary/kanji/:literal` | Dictionary details (senses, examples, kanji; readings, stroke order, words using the kanji), with import |
| `/library?tab=&active=&page=` | The library: words / kanji tabs, active filter, paging |
| `/library/entries/:id`, `/library/kanji/:id` | **Shared detail page** for the library and collections: `MeaningList` (dictionary meanings only toggle; own meanings add / edit / delete), switches for spellings, readings and examples, `NotesEditor` (general and per sense, saved on blur), active, `ItemCollections`, removal |
| `/collections?tab=` | Collections of words / kanji: create and edit (`CollectionFormModal`), delete (`ConfirmModal`) |
| `/collections/:kind/:id` | A collection's items with paging; add from the library (`LibraryPickerModal`), remove; items open the detail page with `?collection=<id>` for the back link (`useBackLink()`) |

The detail is a page, not a modal: it has its own URL, the back button works, and it
has room for editing. List state (tab, filter, page, query) lives in the URL for the
same reason.

## Tests

`tests/unit/` runs in happy-dom: the API client (token, 401), `safeReturnPath`, the
service functions. `tests/components/` runs in the Nuxt environment
(`// @vitest-environment nuxt`, `mountSuspended`): the sign-in middleware,
`MeaningList`, `NotesEditor`, `CollectionFormModal`. They replace `useAuth` with
`tests/fakes.ts` (`mockNuxtImport`), because the real middleware would redirect to
Keycloak while the test app starts.
