# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] — 2026-05-19

### Added

- **JLPT entry level** exposed as `jlpt: int | None` on `Entry` (5 = N5 easiest, 1 = N1 hardest, `null` = no level).
- **Multilingual search**: all three API endpoints (`/search`, `/entries/search`, `/kanji/search`) now accept a `lang` query parameter (ISO 639-1, default `en`). Glosses and kanji meanings are filtered to the requested language.
- **Score breakdown** in debug mode: set `SHODOUKAN_DEBUG=1` to include a `score` object on every `Entry` in search responses, exposing `freq`, `jlpt_bonus`, `fts_rank`, `composite`, `sense_pos`, `total_senses`, and `exact_match`.
- `SHODOUKAN_DEBUG` wired into `docker-compose.yml` and documented in `.env.example`.

### Changed

- **Ranking — common-word bonus** is now computed once per entry (checking both kanji-reading and kana-reading priority fields) instead of independently per field. Prevents the 500 pt baseline from doubling when both forms carry a tier-1 tag (e.g. `ichi1`).
- **Ranking — sense-count damping** uses a linear formula `total × (0.9 + 0.1×total)` instead of quadratic `total²`. Two senses now reduce the score by ~9 % instead of 50 %, making polysemous common words like 食べる rank correctly.
- **Ranking — sense count** in gloss search is now filtered by the target language: only senses that have at least one gloss in the requested language are counted, avoiding inflation from senses in other languages.
- **Ranking — JLPT weight** increased from 50 to 100 per level, giving a 100 pt gap between consecutive JLPT levels (N5 = +500, N4 = +400, …, N1 = +100). This is strong enough to consistently rank beginner-friendly entries above rarer alternatives with equivalent frequency tags.

## [0.1.0] — 2026-04-01

Initial release of the `shodoukan` library and `shodoukan-api` REST API.
