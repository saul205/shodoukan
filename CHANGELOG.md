# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- **shodoukan:** Romaji searches report the right number of results and page through
  all of them. They used to count only meaning matches (`taberu` said 0 results while
  showing 2) and later pages skipped words, because the reading and meaning searches
  were paginated separately and merged afterwards.
- **shodoukan:** Kanji are found by their on-readings. These are stored in katakana and
  were compared with the hiragana of the search, so `kai` didn't list 会, 海 or 回.

### Changed

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
