# API — Usage Guide

The Shodoukan API exposes the dictionary over HTTP. Base URL: `http://localhost:8000`. Full endpoint reference: [technical/api.md](../technical/api.md).

---

## Common flows

### Search for a Japanese word

```
GET /search?q=食べる
```

Returns the top 20 matching entries and all related kanji in one call. Use this for the main search experience.

### Search in another language

```
GET /search?q=eat&lang=en
GET /search?q=comer&lang=es
```

The `lang` parameter (ISO 639-1) filters glosses. Defaults to `en`.

### Search only entries (no kanji)

```
GET /entries/search?q=食べる
```

### Look up a specific entry by ID

```
GET /entries/1358280
```

IDs are JMDict sequence numbers, returned in search results.

### Get the kanji that make up a word

```
GET /entries/1358280/kanji
```

Returns a list of kanji literals (e.g. `["食"]`). Follow up with `/kanji/{literal}` to get full details.

### Browse words that contain a kanji

```
GET /entries/by-kanji/食?limit=10&offset=0
```

### Search kanji by meaning or level

```
GET /kanji/search?q=eat&lang=en
GET /kanji/search?jlpt=5          # all N5 kanji
GET /kanji/search?grade=1         # first-grade elementary kanji
```

### Get a kanji by character

```
GET /kanji/食
```

---

## Pagination

Endpoints that return lists support `limit` (default 20, max 100) and `offset`:

```
GET /entries/search?q=食べる&limit=5&offset=0   # page 1
GET /entries/search?q=食べる&limit=5&offset=5   # page 2
```

The response includes `total` so you can compute how many pages exist.

---

## Debug mode

Set `SHODOUKAN_DEBUG=1` on the API server. Each entry in the response will include a `score` object with the internal ranking values used to order results. Useful for tuning or diagnosing unexpected ordering.
