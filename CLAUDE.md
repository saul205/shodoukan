# shodoukan

See @README.md for a full project overview.

## Project goal

Japanese-English dictionary platform with three main deliverables:

- **Python library** (`packages/shodoukan`): allows developers to build applications on top of the dictionary (lookups, search, etc.)
- **REST API** (`packages/shodoukan-api`): FastAPI service that exposes the library over HTTP
- **Web interface** (`packages/shodoukan-web`): dictionary lookup UI in the style of [Jisho](https://jisho.org/)

## Tech stack

| Layer | Tool |
|---|---|
| Python library + API | FastAPI, SQLAlchemy, Pydantic |
| Code style | PEP 8 |
| Formatter | Ruff |
| Frontend | Nuxt 3 (Vue 3, Composition API), Tailwind CSS, TypeScript |
| Frontend tests | Vitest + Vue Test Utils |
| Backend tests | pytest |

## Repo structure

```
packages/
  shodoukan/        Python library (search, ORM, domain models)
  shodoukan-api/    FastAPI routes, Dockerfile, docker-compose
  shodoukan-web/    Nuxt 3 frontend (see FRONTEND.md for full reference)
tests/
  shodoukan/        Backend unit + integration tests
  shodoukan-api/    API route tests
```

The database pipeline lives in a separate repo (`shodoukan-db`). It downloads JMDict and KANJIDIC2, builds a SQLite database, and publishes it as a GitHub Release asset on a monthly schedule. The DB is consumed by the Python library and the API.

## Data sources

- JMDict (~400k entries): words, readings, senses, glosses, examples
- KANJIDIC2 (~13k kanji): readings, meanings, grade, frequency, JLPT level

## Documentation

Keep these files up to date as the codebase evolves. Read the relevant doc before working on an area; update it when you make changes that affect architecture, conventions, or non-obvious decisions.

See `docs/index.md` for the full documentation index. Quick reference:

| File | Covers |
|---|---|
| `README.md` | High-level overview, API routes, Docker setup, deployment |
| `docs/functional/search.md` | What users can search for, result interpretation, ranking |
| `docs/functional/web.md` | Web UI: search bar, entry cards, kanji sidebar, debug mode |
| `docs/functional/api.md` | API usage flows and examples for consumers |
| `docs/technical/api.md` | Full REST API reference: endpoints, schemas, priority tags |
| `docs/technical/search.md` | Search architecture: query classification, pipelines, scoring formulas |
| `docs/technical/frontend.md` | Frontend architecture, components, responsive layout, Tailwind conventions |

If you add a new package or introduce a significant architectural decision, create or extend the appropriate doc file and add a row to this table.

## Key backend decisions

- `Entry.is_common` is pre-computed on the backend from `EntryORM.has_common` (DB column). The frontend reads it directly — **never derive it from priority tags**.
- Debug mode: set `SHODOUKAN_DEBUG=1` in the API environment to include `ScoreBreakdown` in every entry response. See `packages/shodoukan/src/shodoukan/repositories/entry.py`.
- Ranking uses `JLPT_WEIGHT = 100` (validated). Do not change without re-running ranking tests.
