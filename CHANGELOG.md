# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
