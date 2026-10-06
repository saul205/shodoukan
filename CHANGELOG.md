# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **shodoukan:** `Dictionary.get_kanji_strokes(literal)` returns a character's stroke
  order from KanjiVG (Japanese order, all jōyō kanji and about 6,400 in total). A
  compatibility ideograph is drawn with its canonical form.
- **shodoukan-practice:** Handwriting exercises (`card.handwriting`), the backend: the
  user draws the kanji and the server grades the strokes against KanjiVG (a 0-100
  score, correct / close / wrong, and what's wrong with each stroke: backwards, out of
  order, imprecise, extra, missing). Any kanji of the collections that fits the prompt
  is right. "Close" counts as right but comes back as a review. Kanji without a stroke
  order aren't asked.
- **shodoukan-ui:** `KanjiDrawingPad`, a square to draw a kanji in KanjiVG's space;
  `KanjiStrokeDiagram` takes per-stroke `colors`, a faint `ghost` underneath, `numbers`
  and a CSS `size`; `pointsToPath` and `simplifyStroke` for drawn strokes.
- **shodoukan:** `Dictionary.literals_with_strokes(literals)` tells which characters have
  a stroke order without reading the drawings, and `shodoukan.path_points`
  flattens a stroke's path into evenly spaced points (for comparing
  handwriting).
- **shodoukan-api:** `GET /kanji/{literal}/strokes`.
- **shodoukan-practice:** `GET /dictionary/kanji/{literal}/strokes`.
- **shodoukan-ui:** `KanjiStrokeDiagram` (the numbered character) and
  `getKanjiStrokes`.
- **shodoukan-ui:** `AboutSources`: what shodoukan is, every data source with its
  licence (JMdict, KANJIDIC2, RADKFILE, KanjiVG, Tatoeba / Tanaka Corpus, the JLPT
  lists) and Jisho as inspiration, in English or Spanish.
- **shodoukan-practice-web:** "Acerca de" page, linked from the sidebar, crediting
  the data sources.
- **repo:** Deployment, at no cost. The dictionary API and web stay on Render
  (static site plus a kept-awake API, deployed by CI). The practice stack (API,
  PostgreSQL, Keycloak, practice SPA) runs as "pre" on our own machine with docker
  compose, shared privately through Tailscale: only invited people can reach it, and
  accounts are invite-only. One URL serves `/`, `/practice-api/` and `/idp/`.
  `deploy/deploy.sh` builds any commit (default `origin/main`) in a separate worktree,
  backs up before every deploy, rolls back to any ref, and copies chosen dev users into
  pre (`seed`). Nightly database backups, and each deploy picks up the latest
  dictionary. See `docs/technical/deployment.md`.
- **repo:** CI runs on `develop` too and builds every deployable image.
- **shodoukan-api**, **shodoukan-practice:** `GET /health`.
- **shodoukan-practice:** A Dockerfile for the API, with the dictionary baked in; it
  also runs the migrations.
- **shodoukan:** `shodoukan-setup` sends `GITHUB_TOKEN` when set, avoiding GitHub's
  anonymous rate limit.

- **shodoukan-practice-web:** Statistics: each exercise's page shows its totals,
  accuracy per direction and the items missed most; "Estadísticas" shows them over
  every exercise, with the answers per day over the last 7, 30 or 90 days, a table
  per exercise and the words and kanji missed most. Missed items open their detail.
- **shodoukan-practice-web:** Exercise history: each exercise has its own page with
  what it studies, "Empezar" or "Continuar", and its sessions (date, duration,
  accuracy). A finished session shows its result and a card-by-card review, one
  collapsible line per card, all or only the missed ones.
- **shodoukan-practice:** Skip a question with `{"type": "skip"}` as the answer: it
  counts as a miss, comes back as a review and returns its solution.
- **shodoukan-practice-web:** Play exercises: "Empezar" opens a session with one card
  at a time; pick an option with a click or its number key, see the back with the
  right option in green and a wrong pick in red, open any item's detail without
  leaving, skip a card ("Saltar", counted as a miss) and go on with "Siguiente" or
  Enter. The card and options fill the screen and don't move when answering. "Continuar" (on the exercise list and
  the home page) resumes the open session; "Terminar" shows how it went.
- **shodoukan-practice:** Session history and statistics. `GET /exercise-sessions`
  lists the user's sessions, newest first, without their questions, filtered by
  exercise and by `status` (`open` or `finished`; `status=open&limit=1` is the session
  to resume). `GET /exercises/{id}/statistics` gives an exercise's totals, accuracy
  per direction and most missed items; `GET /statistics?days=30&tz=...` gives the
  same over every exercise, the answers of each day in the user's time zone, a
  summary per exercise, and the words and kanji missed most. Missed items are named
  as they are now in the library. Every question in a session response now carries
  its `type` (`"card.choice"`).
- **shodoukan-practice-web:** "Ejercicios": list, create, edit and delete exercises.
  The form picks one or more collections of words or kanji, the directions (fields
  shown → field asked), what the back of the card shows and the number of options,
  and checks the same rules as the API before saving.
- **shodoukan-practice:** Exercise sessions to study an exercise for as long as the
  user likes: `POST /exercises/{id}/sessions` starts one with its first question,
  `POST /exercise-sessions/{id}/answer` grades the active question and returns the
  next, `POST /exercise-sessions/{id}/finish` ends it, and `GET
  /exercise-sessions/{id}` reads it back. Every item comes up once per round, missed
  ones come back a few cards later, and idle sessions close on their own. A wrong
  option is never also a right answer (shared readings, homophones, synonyms,
  katakana/hiragana), words are asked by their usual form, and solutions stay hidden
  until answered. Sessions keep a snapshot of every question for history and
  statistics.
- **shodoukan-practice:** Saved exercises (`/exercises`: create, list, get, replace,
  delete). An exercise studies words or kanji from the user's collections; its
  settings are a choice card with directions (fields shown → field asked), back-of-card
  fields, number of options and questions per session. Sessions come next.
- **shodoukan-practice:** Search the library and collections: `q` (spelling, reading,
  romaji converted to kana, or meaning) and `meaning_lang` on `GET /library/entries`,
  `GET /library/kanji` and `GET /collections/{kind}/{id}/items`, best match first;
  hidden readings and meanings count. `not_in_collection` lists what can still be added
  to a collection.
- **shodoukan-practice-web:** A search box in the library, in each collection and in
  the "add to collection" picker, which now lists only what isn't in the collection
  yet.
- **shodoukan-practice:** `GET /collections/{entries,kanji}/{id}/items` takes `active`
  like the library listings. Without it, deactivated items are now listed too (they
  used to be hidden).
- **shodoukan-practice:** `POST /library/entries` and `POST /library/kanji` take
  optional `collection_ids` to import an item straight into collections, in one
  transaction: an unknown collection imports nothing.
- **shodoukan-practice-web:** The dictionary's import button has a folder half that
  lists the user's collections: tick one to import the item straight into it, or to
  add an imported item to it or take it out; "Nueva colección" creates one.
- **shodoukan-practice-web:** A library kanji's page lists a few dictionary words that
  use it (imported ones open the library copy), with a link to search the dictionary
  for it.
- **shodoukan-practice-web:** A library word's page shows its kanji as the dictionary
  does, ready to import or put in a collection; imported ones open the library copy.

### Fixed

- **shodoukan-web / shodoukan-practice-web:** stroke order was blank for Japanese
  forms such as 楽, 気 or 図, and used the Chinese order where it showed.
- **shodoukan:** Romaji searches report the right number of results and page through
  all of them. They used to count only meaning matches (`taberu` said 0 results while
  showing 2) and later pages skipped words, because the reading and meaning searches
  were paginated separately and merged afterwards.
- **shodoukan:** Kanji are found by their on-readings. These are stored in katakana and
  were compared with the hiragana of the search, so `kai` didn't list 会, 海 or 回.

### Changed

- **shodoukan-practice:** Session questions are stored by `type`, with what only that
  type has in a `details` JSON column; a choice card's options and right option move
  there (migration `33f2afbdd7cf`). Session responses return each question by type.
- **shodoukan-ui:** `KanjiStrokeAnimator` and `KanjiStrokeGrid` take the KanjiVG
  `strokes` as a prop instead of a `literal`, and render plain SVG (no `<ClientOnly>`
  needed).
- **shodoukan-web / shodoukan-practice-web:** the kanji pages fetch stroke order from
  their API. The web app's diagram no longer loads from raw.githack.com.
- **shodoukan-web:** the Sources page is merged into About, which now credits every
  data source; `/sources` redirects there.
- **shodoukan-practice-web:** Fits phones better. On a dictionary word or kanji
  page the import buttons take their own row below it (and stack on very narrow
  screens), so the meanings keep the width. During an exercise the card shows only
  its front, then turns to show only its back: the prompt as the headline, the
  answer, then the other fields smaller. The card keeps room for its back from
  the start, so turning it doesn't resize it (a longer back grows it). Options
  grow into the room the card doesn't need, in one column on phones (two with
  short texts, 7–8 options or on short screens), so a session fits a phone screen
  without scrolling.
- **shodoukan-web:** The dictionary frontend is a static SPA (`ssr: false`, `nuxt
  generate`), published on a Render Static Site.
- **shodoukan-practice-web:** The identity provider URL can be relative to the site
  (`/idp/realms/shodoukan`).
- **shodoukan-practice-web:** The dictionary's kanji page shows the meanings larger,
  filling the height of the kanji, with its strokes, grade and the rest below them.
- **shodoukan-ui, shodoukan-web, shodoukan-practice-web:** Kanji readings list kun'yomi
  before on'yomi everywhere (`KanjiCard` and the kanji pages), as the compact cards
  already did.
- **shodoukan-practice-web:** A collection's page lists its deactivated items too, marked
  as inactive, with the library's Todos / Activos / Inactivos filter.
- **shodoukan-practice-web:** One collection picker for the dictionary and the library:
  an icon with a searchable list where typing a new name creates the collection with
  the item in it. In the dictionary it ticks the collections the item is in, to take it
  out; on a library page (an icon in the "Colecciones" header, instead of a full-width
  selector) it lists only the others.
- **shodoukan:** Entry search ranks every match with one score, `match_tier × 2000 +
  popularity`, in a single query: reading matches by exact/prefix, meaning matches by
  bm25 relative to the best match of the search. Japanese searches keep their order;
  romaji searches interleave readings and meanings.
- **shodoukan:** Meaning matches are decayed by the position of the matched sense only
  (`/ log2(position + 2)`) instead of by the number of senses, so common words with many
  meanings (水) are no longer pushed down.
- **shodoukan:** In romaji searches, a word found both by reading and by meaning is
  ranked by its reading. Words whose definition is their own romaji (水ようかん, "mizu
  yōkan") no longer rank above common words starting with the same reading (湖, 水着 for
  `mizu`); translations found only by meaning (同じ for `same`) keep their rank.
- **shodoukan:** Kanji searches rank by the kind of match first, then by popularity: an
  exact reading or meaning, then a reading prefix or a meaning that contains the search,
  then meanings that only start with it. `au` now lists 合 and 遇 (あう) instead of 図
  ("audacious") and 秋 ("autumn"); `same` still lists both 同 and 鮫 (さめ).
- **shodoukan-ui:** The debug bar shows the new `score` as the sort value, with `tier`
  and `relevance`.

### Removed

- **shodoukan-ui:** the `hanzi-writer` dependency.

## [0.2.0] — 2026-05-21

### Added

- **Romaji search**: queries written in Hepburn romaji (e.g. `taberu`) are converted to hiragana before searching. Falls back to gloss search if the input cannot be fully converted (e.g. `water`).
- **JLPT entry level** exposed as `jlpt: int | None` on `Entry` (5 = N5 easiest, 1 = N1 hardest, `null` = no level).
- **Multilingual support**: all three API endpoints (`/search`, `/entries/search`, `/kanji/search`) accept a `lang` query parameter (ISO 639-1, default `en`). Glosses and kanji meanings are filtered to the requested language.
- **Score breakdown** in debug mode: set `SHODOUKAN_DEBUG=1` to add a `score` object to every `Entry` in search responses (`freq`, `jlpt_bonus`, `fts_rank`, `composite`, `sense_pos`, `total_senses`, `exact_match`). Wired into `docker-compose.yml` and documented in `.env.example`.

### Changed

- **Ranking — common-word bonus** is now computed once per entry across both kanji-reading and kana-reading priority fields. Previously it fired per field, doubling the 500 pt baseline when both forms carried a tier-1 tag.
- **Ranking — sense-count damping** switched from quadratic (`total²`) to linear (`total × (0.9 + 0.1×total)`). Two senses now reduce the score by ~9 % instead of 50 %.
- **Ranking — sense count** in gloss search only counts senses that have at least one gloss in the target language, preventing inflation from senses in other languages.
- **Ranking — JLPT weight** raised from 50 to 100 per level (N5 = +500 … N1 = +100), consistently pushing beginner-friendly entries above rarer alternatives with equivalent frequency tags.

## [0.1.0] — 2026-04-01

Initial release of the `shodoukan` library and `shodoukan-api` REST API.
