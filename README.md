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
    strokes = d.get_kanji_strokes("楽")             # KanjiVG stroke order
    drawn   = d.literals_with_strokes(["楽", "水"])  # which ones have a drawing

from shodoukan.utils.svg_path import path_points
points = path_points(strokes.strokes[0].path)        # a stroke as evenly spaced points
```

Supports lookup by kanji, kana, Hepburn romaji, or gloss in any JMDict language. Each `Entry` includes its JLPT level (`jlpt: int | None`). Stroke order comes from [KanjiVG](https://kanjivg.tagaini.net/) (Japanese stroke order, all jōyō kanji and about 6,400 in total). See [packages/shodoukan/](packages/shodoukan/) for the full API.

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
| GET | `/kanji/{literal}/strokes` | Get a character's stroke order (KanjiVG) |
| GET | `/health` | Liveness check |

Search endpoints accept `lang` (ISO 639-1, default `en`) and `limit` / `offset` for pagination.

Interactive docs available at `/docs` when the server is running.

### `shodoukan-practice` — Practice app *(in progress)*

Backend for studying with the dictionary: each user imports entries and kanji into a
personal library, customises them, and groups them into collections (which double as
tags) to practise with. Built so far: the domain, PostgreSQL persistence, sign-in
through Keycloak (OAuth2 / OpenID Connect), its own dictionary search
(`GET /dictionary/search`), and importing entries and kanji (`POST /library/entries`,
`POST /library/kanji`), grouping them into collections (`/collections/entries`,
`/collections/kanji`), searching the library and its collections (`q` on the list
endpoints), and exercises: saved choice-card exercises (`/exercises`), open-ended
study sessions graded on the server (`/exercises/{id}/sessions`,
`/exercise-sessions`), their history and statistics (`/exercises/{id}/statistics`,
`/statistics`). See the [practice app documentation](docs/practice/README.md).

### `shodoukan-web` — Dictionary frontend *(in progress)*

Dictionary lookup UI in the style of [Jisho](https://jisho.org/): a Nuxt 3 SPA,
published as a static site. See the [frontend docs](docs/technical/frontend.md).

### `shodoukan-practice-web` — Practice frontend *(in progress)*

Nuxt 4 + Nuxt UI app for the practice API on <http://localhost:3001>: sign in with
Keycloak, then search the dictionary and import, customise your library (meanings,
notes, readings), group it into collections, and practise them with exercises, with a
history, a review of each session and statistics. See the
[frontend docs](docs/practice/technical/frontend.md).

---

## Documentation

- [Documentation index](docs/index.md): functional and technical docs for search, the
  API and the web interface.
- [Practice app](docs/practice/README.md): [functional](docs/practice/functional/README.md)
  and [technical](docs/practice/technical/README.md) documentation.

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

## Deployment

Free of charge, split in two:

- **Dictionary** (`shodoukan-api` and the `shodoukan-web` static SPA): Render. Every
  push to `main` that passes CI triggers their deploy hooks.
- **Practice stack** (practice API, PostgreSQL, Keycloak, practice SPA): "pre",
  self-hosted with docker compose and shared privately through Tailscale. It's only
  reachable by the people the node is shared with, and accounts are invite-only.

```bash
cp deploy/.env.pre.example deploy/.env.pre   # once, then set the passwords
deploy/deploy.sh                             # build origin/main and (re)start pre
```

Setup, inviting people, backups and rollbacks: [deployment](docs/technical/deployment.md).

---

## Development

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e packages/shodoukan[dev] -e packages/shodoukan-api[dev] -e packages/shodoukan-practice[dev]
shodoukan-setup  # download the database
```

### Practice database (PostgreSQL)

`shodoukan-practice` stores user data in PostgreSQL. Copy the "Practice database"
block from `.env.example` into your `.env.dev` (with your own password), then:

```bash
docker compose up -d practice-db          # local Postgres on 127.0.0.1:5432
set -a; . ./.env.dev; set +a              # export PRACTICE_DATABASE_URL
alembic -c packages/shodoukan-practice/alembic.ini upgrade head
```

### Practice API and sign-in (Keycloak)

```bash
cp .env.keycloak.example .env.keycloak    # Keycloak and its own database; set passwords
docker compose up -d keycloak             # http://localhost:8080 (starts keycloak-db too)
set -a; . ./.env.dev; set +a              # AUTH_ISSUER, AUTH_AUDIENCE, PRACTICE_DATABASE_URL
uvicorn shodoukan_practice.api.app:app --port 8001 --reload
```

Open <http://localhost:8001/docs> and click **Authorize** to sign in (local user
`dev` / `dev`). See the [authentication docs](docs/practice/technical/api/authentication.md).

### Practice frontend

With the practice API and Keycloak running (above):

```bash
pnpm install
pnpm --filter shodoukan-ui build               # shared components
pnpm --filter shodoukan-practice-web dev       # http://localhost:3001 (sign in as dev / dev)
```

After changing an ORM model, create a migration and review it:

```bash
alembic -c packages/shodoukan-practice/alembic.ini revision --autogenerate -m "Describe the change"
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
pytest tests/shodoukan-practice
```

### Lint and type check

```bash
ruff check . && ruff format --check .
mypy  # config in mypy.ini; strict for shodoukan-practice
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
