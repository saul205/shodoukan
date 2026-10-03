# Search Architecture

## Overview

`Dictionary.search()` runs two independent pipelines and combines them into a `SearchResult`:

- **Entry pipeline** — finds dictionary entries (words, verbs, phrases)
- **Kanji pipeline** — finds individual kanji characters

The two results are never cross-pollinated: kanji are not derived from entry results, and entries are not filtered by kanji results.

---

## Query Classification

Queries are classified in this order:

| Condition | Entry search | Kanji method |
|-----------|-------------|--------------|
| `is_kanji_only(query)` — every character is a CJK ideograph | reading matches | Direct literal lookup for each character |
| `is_japanese(query)` — contains any kanji or kana | reading matches | `search` → reading path |
| `is_romaji(query)` — ASCII letters/apostrophes/hyphens only | reading matches (as hiragana) **and** gloss matches (as typed), ranked together | `search(hiragana)` → reading path |
| Fallback (other language gloss) | gloss matches | `search` → meaning path |

Romaji is converted to hiragana via Hepburn mapping before use. If conversion fails (e.g. "water" contains non-romaji characters) the query falls through to the gloss path.

---

## Entry Search

Every entry search is one SQL query: `EntryRepository.search(reading_query, gloss_query,
lang, limit, offset)` (code: `repositories/entry.py`, constants: `repositories/scoring.py`).
`search_by_japanese` and `search_by_gloss` call it with one branch. Each matching entry
gets a **score in a unit shared by both kinds of match**, so reading and gloss matches
can be ranked, counted and paginated together.

```
score      = match_tier × TIER_WEIGHT + popularity          TIER_WEIGHT = 2000
popularity = freq_score + coalesce(jlpt, 0) × JLPT_WEIGHT   JLPT_WEIGHT = 100
```

`freq_score` is 0–560 and the JLPT bonus 0–500, so popularity stays below ~1100 <
`TIER_WEIGHT`: **a better tier always wins**, and popularity orders entries within a
tier.

### Reading matches

Entries whose spelling or reading equals or starts with the query:

```
kanji_reading == query  OR  kanji_reading LIKE query%
OR reading == query     OR  reading LIKE query%
```

| Tier | When |
|---|---|
| 3 | a spelling or reading **equals** the query |
| 2 | one only **starts with** it |

Popularity is used as is. This keeps the earlier order: exact matches first, then by
popularity.

### Gloss matches

SQLite FTS5 on `glosses`, in the requested language. The phrase is tried first; if it
matches nothing in that language, a prefix match is used. (The check starts from the
FTS index in a materialized CTE: joined with `LIMIT 1`, SQLite would scan every gloss
of the language.)

**Tier — bm25 relative to the best match of the query.** Gloss matches are rarely
exact ("eat" vs the gloss "to eat"), so the match quality comes from FTS5's bm25 rank,
which already favours short glosses. An entry's rank is that of its best matching
gloss, and

```
relevance = rank / best_rank_of_the_query      (ranks are negative: 1 = the best match)
```

| Tier | When |
|---|---|
| 3 | relevance ≥ 0.9 (`GLOSS_TIER_3_RELEVANCE`) |
| 2 | relevance ≥ 0.5 (`GLOSS_TIER_2_RELEVANCE`) |
| 1 | weaker |

Relevance is relative to the query: the best gloss match is tier 3 even when it's a
weak match overall.

**Popularity — decayed by the matched sense's position (composite):**

```
composite = (freq_score + jlpt_pts) / log2(sense_pos + 2)
```

`sense_pos` is the zero-based position of the matched sense among the entry's senses in
that language (sense 1 → ×1.00, 2 → ×0.63, 3 → ×0.50, 5 → ×0.39, 9 → ×0.30). Only the
position counts, not how many senses the entry has, so a common word with many senses
(水) isn't penalised for a match in its first sense. `log2` is an SQLite math function;
`db/connection.py` registers a Python one when the SQLite build lacks it.

### Combining, ordering and pagination

```
reading matches  ┐
                 ├─ UNION ALL ─ GROUP BY id (reading row) ─ ORDER BY ─ LIMIT/OFFSET
gloss matches    ┘                                          + COUNT(*) OVER ()
```

- An entry found both ways counts once and is **ranked by its reading match** (each row
  carries `source`, 0 = reading, 1 = gloss; SQLite takes the other columns of a `MIN()`
  group from the row with the min). Only romaji searches run both branches, and there a
  gloss that matches the same romaji as the entry's own reading is a transliteration,
  not a translation: JMdict uses the romaji as the gloss for untranslatable terms
  (`mizu yōkan` for 水ようかん, `kami-sama` for 神様). Ranked as glosses they'd be the
  best gloss matches of the query (tier 3), above every prefix reading. Entries found
  only by gloss keep their gloss tier, because romaji can't be told apart from English
  or Spanish: for `same` (also さめ) the translation 同じ is still a tier-3 match, ahead
  of 鮫. Capping all gloss matches in romaji searches was rejected for that reason.
- Order: `score DESC`, then the raw bm25 rank (reading matches first), then `id`, so
  the order is total and stable.
- The total is `COUNT(*) OVER ()` over all matches; when the page is past the end, a
  separate count. Pages partition the results: no entry is skipped or repeated.

Before this, a romaji search ran both searches with their own `LIMIT/OFFSET`, merged
the pages in Python and reported the gloss total only (`taberu` → total 0 with 2
results), so later pages dropped entries.

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
