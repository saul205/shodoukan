# Search Architecture

## Overview

`Dictionary.search()` runs two independent pipelines and combines them into a `SearchResult`:

- **Entry pipeline** — finds dictionary entries (words, verbs, phrases)
- **Kanji pipeline** — finds individual kanji characters

The two results are never cross-pollinated: kanji are not derived from entry results, and entries are not filtered by kanji results.

---

## Query Classification

Queries are classified in this order:

| Condition | Entry method | Kanji method |
|-----------|-------------|--------------|
| `is_kanji_only(query)` — every character is a CJK ideograph | `search_by_japanese` | Direct literal lookup for each character |
| `is_japanese(query)` — contains any kanji or kana | `search_by_japanese` | `search` → reading path |
| `is_romaji(query)` — ASCII letters/apostrophes/hyphens only | `search_by_japanese(hiragana)` | `search(hiragana)` → reading path |
| Fallback (other language gloss) | `search_by_gloss` | `search` → meaning path |

Romaji is converted to hiragana via Hepburn mapping before use. If conversion fails (e.g. "water" contains non-romaji characters) the query falls through to the gloss path.

---

## Entry Search

### Japanese / romaji → `search_by_japanese`

Matches entries where any **kanji reading starts with** the query or any **kana reading equals or starts with** the query. The match condition is:

```
kanji_reading == query  OR  kanji_reading LIKE query%
OR reading == query     OR  reading LIKE query%
```

**Scoring:**
```
score = freq_score + coalesce(jlpt, 0) * JLPT_WEIGHT   (JLPT_WEIGHT = 100)
```

Results are ordered: exact matches (full kanji or kana reading equals query) first, then by score descending.

### Gloss / other language → `search_by_gloss`

Uses SQLite FTS5 on the `glosses` table. Tries an exact phrase match first; falls back to prefix matching if no results.

**Scoring (composite):**
```
composite = (freq_score + jlpt_pts) * (total_senses - sense_pos)
            / (total_senses * (0.9 + 0.1 * total_senses))
```

- `jlpt_pts = coalesce(jlpt, 0) * JLPT_WEIGHT`
- `sense_pos` = zero-based position of the matched sense in the entry's sense list for this language (earlier = more primary)
- `total_senses` = total number of senses the entry has in this language

Results are ordered: FTS rank (best match) first, then composite score descending within the same rank tier.

---

## Kanji Search

### Literal-only path (`is_kanji_only`)

Each character in the query is looked up individually in the `kanji` table. Results are sorted by kanji score (see below) and returned as a flat list.

### Reading path (Japanese / romaji queries)

Searches `on_readings` and `kun_readings` JSON columns. The match condition covers:

- Exact on-reading match (`value = query`)
- Exact kun-reading match (`value = query`)
- On-reading prefix match (`value LIKE query%`)
- Kun-reading with okurigana prefix (`value LIKE query.%`)

**Ordering:** exact matches first, then kanji score descending.

Note: kun-readings are stored with an okurigana separator dot (e.g. `た.べる`). Searching `たべる` will not match `た.べる` through the exact or prefix paths; it matches only if the pre-dot stem equals the query.

### Meaning path (gloss / other language)

Uses SQLite FTS5 on the `kanji_meanings` table (filtered by language). Tries exact phrase then prefix fallback.

**Ordering:** best FTS rank across all meanings for that kanji (`min(rank)`) first, then kanji score descending.

---

## Kanji Scoring

```
kanji_score = jlpt * 10_000
            + coalesce(11 - grade, 0) * 1_000
            - coalesce(freq, 99_999)
```

| Field | Direction | Notes |
|-------|-----------|-------|
| `jlpt` | Higher = better | 1–5; N5 (most common) = 5. NULL = 0 pts |
| `grade` | Lower = better (more basic) | 1–6 elementary, 8 secondary, 9–10 jinmeiyo. `11 - grade` inverts so grade 1 scores highest; NULL = 0 pts |
| `freq` | Lower = better | Frequency rank 1–2500 (1 = most common). NULL penalised as 99 999 |

This formula is applied both in SQL (for repository-level ordering) and in Python via `kanji_score_value(k: Kanji)` (for in-memory sorting of the literal-only path).
