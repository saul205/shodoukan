# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

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

- **shodoukan:** Romaji searches report the right number of results and page through
  all of them. They used to count only meaning matches (`taberu` said 0 results while
  showing 2) and later pages skipped words, because the reading and meaning searches
  were paginated separately and merged afterwards.
- **shodoukan:** Kanji are found by their on-readings. These are stored in katakana and
  were compared with the hiragana of the search, so `kai` didn't list 会, 海 or 回.

### Changed

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
