# shodoukan

A Japanese-English dictionary platform built around the [JMDict](https://www.edrdg.org/jmdict/j_jmdict.html) and [KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project) datasets.

## Components

### `shodoukan-db` (separate repo)

Rust pipeline that downloads JMDict and KANJIDIC2, processes them, and publishes a SQLite database as a GitHub Release asset on a monthly schedule. The database is the shared artifact consumed by all other components.

GitHub repository: [shodoukan-db](https://github.com/saul205/shodoukan-db)

### `shodoukan` — Python library

Package for building applications on top of the dictionary.

```python
from shodoukan import Dictionary

with Dictionary() as d:
    results = d.search_entries("日本語", limit=10)   # kanji / kana
    results = d.search_entries("taberu")             # romaji → hiragana
    results = d.search_entries("comer", lang="es")   # multilingual gloss
    kanji   = d.get_kanji("日")
```

Supports lookup by kanji, kana, Hepburn romaji, or gloss in any JMDict language. Each `Entry` includes its JLPT level (`jlpt: int | None`). See [packages/shodoukan/](packages/shodoukan/) for the full API.

### `shodoukan-api` — REST API

FastAPI application that exposes the library over HTTP. See [packages/shodoukan-api/](packages/shodoukan-api/) for details.

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/search` | Search entries and kanji together |
| GET | `/entries/search` | Search dictionary entries |
| GET | `/entries/{id}` | Get entry by ID |
| GET | `/entries/{id}/kanji` | Get kanji linked to an entry |
| GET | `/entries/by-kanji/{literal}` | Get entries that contain a kanji |
| GET | `/kanji/search` | Search kanji |
| GET | `/kanji/{literal}` | Get kanji by literal |

Search endpoints accept `lang` (ISO 639-1, default `en`) and `limit` / `offset` for pagination.

Interactive docs available at `/docs` when the server is running.

### Web interface *(planned)*

Dictionary lookup UI in the style of [Jisho](https://jisho.org/).

---

## Running with Docker

### Quick start

```bash
docker compose up --build
```

The database is downloaded automatically during the image build. The API will be available at <http://localhost:8000>.

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | `8000` | Port to expose the API on |
| `SHODOUKAN_DEBUG` | `0` | Set to `1` to include score breakdown in search responses |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins. Use `*` in development; set to your domain in production (e.g. `https://shodoukan.onrender.com`). |

---

## Deployment (Render)

Every push to `main` that passes CI is deployed automatically to Render.

### First-time setup

1. Create a new **Web Service** on [Render](https://render.com) pointing to this repository.
2. Set the build command to `docker build` (Render detects the Dockerfile automatically).
3. Add the following environment variables in the Render dashboard:

| Variable | Value |
|----------|-------|
| `CORS_ORIGINS` | Your frontend domain, e.g. `https://shodoukan.onrender.com` |
| `SHODOUKAN_DEBUG` | `0` |

After that, every push to `main` triggers a new deploy.

---

## Development

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e packages/shodoukan[dev] -e packages/shodoukan-api[dev]
shodoukan-setup  # download the database
```

### Running locally

```bash
uvicorn shodoukan_api.app:app --reload
```

Or via the entry point:

```bash
shodoukan-api
```

### Tests

```bash
pytest tests/shodoukan
pytest tests/shodoukan-api
```

### CLI

```bash
shodoukan search "water"
shodoukan kanji-search --jlpt 5
shodoukan entry-search "食べる"
```

---

## Data sources

- **JMDict** (~400k entries): words, readings, senses, multilingual glosses, and example sentences.
- **KANJIDIC2** (~13k kanji): on/kun readings, meanings, school grade, frequency rank, and JLPT level.

Both datasets are maintained by [EDRDG](https://www.edrdg.org/) and distributed under [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
