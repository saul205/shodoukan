# Shodoukan API — Technical Reference

Base URL: `http://localhost:8000`

Interactive docs (Swagger): [`/docs`](http://localhost:8000/docs)

---

## Common parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang` | string | `en` | Language code for filtering results. See [language support](#language-support). |
| `limit` | integer | `20` | Max items per page. Range: 1–100. |
| `offset` | integer | `0` | Number of items to skip for pagination. |

---

## Language support

The `lang` parameter uses ISO 639-1 codes. Supported values differ by endpoint:

| Code | Language | Entries & Search | Kanji |
|------|----------|:----------------:|:-----:|
| `en` | English  | ✓ | ✓ |
| `es` | Spanish  | ✓ | ✓ |
| `fr` | French   | ✓ | ✓ |
| `de` | German   | ✓ | ✓ |
| `ru` | Russian  | ✓ | — |
| `nl` | Dutch    | ✓ | — |
| `hu` | Hungarian | ✓ | — |
| `sl` | Slovenian | ✓ | — |

---

## Endpoints

### `GET /search`

Combined search that returns both dictionary entries and kanji in a single request.

**Query parameters**

| Parameter | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `q` | string | ✓ | — | Search term. Accepts kanji, kana, romaji, or a gloss in the target language. Min length: 1. |
| `lang` | string | | `en` | Filters entry glosses by language. |
| `limit` | integer | | `20` | Applied to the entries page. |
| `offset` | integer | | `0` | Applied to the entries page. |

**Response** `200 OK`

```json
{
  "entries": {
    "items": [ Entry ],
    "total": 405,
    "limit": 20,
    "offset": 0
  },
  "kanji": [ Kanji ]
}
```

---

### `GET /entries/search`

Searches dictionary entries only.

**Query parameters**

| Parameter | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `q` | string | ✓ | — | Search term. Min length: 1. |
| `lang` | string | | `en` | Filters glosses by language. |
| `limit` | integer | | `20` | |
| `offset` | integer | | `0` | |

**Response** `200 OK` — `Page<Entry>`

---

### `GET /entries/{entry_id}`

Returns a single entry by its JMDict sequence number.

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entry_id` | integer | JMDict sequence number. |

**Response**

| Status | Body | When |
|--------|------|------|
| `200 OK` | `Entry` | Entry found. |
| `404 Not Found` | `{"detail": "Entry not found"}` | Unknown ID. |

---

### `GET /entries/{entry_id}/kanji`

Returns the individual kanji characters contained in the written forms of an entry.

**Response** `200 OK` — `EntryKanjiLink[]`

---

### `GET /entries/by-kanji/{literal}`

Returns all entries that contain the specified kanji character.

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `literal` | string | A single kanji character (e.g. `食`). |

**Query parameters**: `limit`, `offset`

**Response** `200 OK` — `Page<Entry>`

---

### `GET /kanji/search`

Searches kanji. At least one of `q`, `grade`, or `jlpt` must be provided.

**Query parameters**

| Parameter | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `q` | string | * | — | Search by kanji character or meaning in the target language. |
| `lang` | string | | `en` | Language for meaning matching. Supported: `en`, `es`, `fr`, `de`. |
| `grade` | integer | * | — | Filter by Joyo school grade (1–6 = elementary, 8 = junior high). Range: 1–10. |
| `jlpt` | integer | * | — | Filter by JLPT level (1 = N1 … 5 = N5). Range: 1–5. |
| `limit` | integer | | `20` | |
| `offset` | integer | | `0` | |

\* At least one of `q`, `grade`, or `jlpt` is required. Returns `422` if none are provided.

**Response** `200 OK` — `Page<Kanji>`

---

### `GET /kanji/{literal}`

Returns a single kanji by its character.

**Response**

| Status | Body | When |
|--------|------|------|
| `200 OK` | `Kanji` | Kanji found. |
| `404 Not Found` | `{"detail": "Kanji not found"}` | Unknown character. |

---

## Schemas

### `Page<T>`

```json
{
  "items":  [ T ],
  "total":  405,
  "limit":  20,
  "offset": 0
}
```

### `Entry`

```json
{
  "id": 1358280,
  "jlpt": 5,
  "is_common": true,
  "kanji_readings": [
    {
      "id": 28429,
      "kanji": "食べる",
      "priority": ["ichi1", "news2"],
      "info": []
    }
  ],
  "readings": [
    {
      "id": 43238,
      "text": "たべる",
      "no_kanji": false,
      "priority": ["ichi1", "news2"],
      "info": [],
      "restricted_to": []
    }
  ],
  "senses": [
    {
      "id": 179130,
      "pos": ["Ichidan verb", "transitive verb"],
      "misc": [],
      "dialects": [],
      "info": [],
      "glosses": [
        { "id": 427768, "text": "to eat", "type": null, "lang": "eng" }
      ],
      "cross_references": [],
      "examples": []
    }
  ],
  "score": null
}
```

**`is_common`** — pre-computed on the backend from the `has_common` DB column. `true` for words that appear frequently in newspapers and general use. Do not derive this from `priority` tags.

**`score`** — `null` by default. Populated with a `ScoreBreakdown` object when the API runs with `SHODOUKAN_DEBUG=1`.

### `ScoreBreakdown` (debug mode only)

```json
{
  "freq": 510,
  "jlpt_bonus": 500,
  "exact_match": true,
  "fts_rank": null,
  "sense_pos": null,
  "total_senses": null,
  "composite": null
}
```

Japanese search populates `freq`, `jlpt_bonus`, `exact_match`. Gloss search populates `freq`, `jlpt_bonus`, `fts_rank`, `sense_pos`, `total_senses`, `composite`. The effective sort key is `composite` (gloss) or `freq + jlpt_bonus` (Japanese).

### `EntryKanjiLink`

```json
{ "literal": "食" }
```

### `Kanji`

```json
{
  "literal": "食",
  "grade": 2,
  "stroke_count": 9,
  "freq": 316,
  "jlpt": 4,
  "on_readings": ["ショク", "ジキ"],
  "kun_readings": ["た.べる", "た.う", "くら.う"],
  "nanori": [],
  "meanings": [
    { "text": "eat", "lang": "en" },
    { "text": "food", "lang": "en" }
  ]
}
```

### `SearchResult`

```json
{
  "entries": { "items": [ Entry ], "total": 405, "limit": 20, "offset": 0 },
  "kanji":   [ Kanji ]
}
```

---

## Priority tags

The `priority` field on readings uses JMDict frequency codes:

| Tag | Tier | Points | Meaning |
|-----|------|--------|---------|
| `ichi1`, `spec1`, `news1`, `gai1` | 1 | 10 each | Most common words |
| `ichi2`, `spec2`, `news2`, `gai2` | 2 | 5 each | Common words |
| `nfXX` | — | — | Frequency rank band (01 = top 500 words) |
