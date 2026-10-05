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
| Practice database | PostgreSQL, Alembic (tests on SQLite) |
| Code style | PEP 8 |
| Formatter | Ruff |
| Frontend | Nuxt 3 (Vue 3, Composition API), Tailwind CSS, TypeScript; the practice frontend uses Nuxt 4 + Nuxt UI 4 (Tailwind 4) |
| Frontend tests | Vitest + Vue Test Utils |
| Backend tests | pytest |

## Repo structure

```
packages/
  shodoukan/           Python library (search, ORM, domain models)
  shodoukan-api/       FastAPI routes, Dockerfile, docker-compose
  shodoukan-practice/  Practice/exercises backend: users' imported entries/kanji and collections (domain, PostgreSQL persistence, dictionary gateway, import use cases and endpoints with Keycloak auth). Docs: `docs/practice/`
  shodoukan-ui/        Shared Vue component library (EntryCard, KanjiCard, SearchBar, ...), own Tailwind build
  shodoukan-web/       Nuxt 3 dictionary frontend (docs/technical/frontend.md)
  shodoukan-practice-web/  Nuxt 4 + Nuxt UI practice frontend on :3001, Keycloak sign-in (docs/practice/technical/frontend.md)
deploy/                Self-hosted practice stack ("pre"): compose.yml, Caddy, private Tailscale tunnel, deploy.sh (docs/technical/deployment.md)
docker/keycloak/       Dev realm; production Keycloak image and realm (prod/)
tests/
  shodoukan/           Backend unit + integration tests
  shodoukan-api/       API route tests
  shodoukan-practice/  Practice backend tests (domain, application, infrastructure, api)
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
| `docs/technical/deployment.md` | Deployment: Render (dictionary), the self-hosted pre (`deploy/`), Tailscale access, CI/CD, backups |
| `docs/practice/README.md` | Practice app entry point: status and map of its docs |
| `docs/practice/technical/frontend.md` | Practice frontend: sign-in flow, API client, screens, tests |
| `docs/practice/technical/README.md` | Practice app technical docs index, plus the "where to document what" table |

If you add a new package or introduce a significant architectural decision, create or extend the appropriate doc file and add a row to this table.

## Key backend decisions

- `Entry.is_common` is pre-computed on the backend from `EntryORM.has_common` (DB column). The frontend reads it directly — **never derive it from priority tags**.
- Debug mode: set `SHODOUKAN_DEBUG=1` in the API environment to include `ScoreBreakdown` in every entry response. See `packages/shodoukan/src/shodoukan/repositories/entry.py`.
- Ranking uses `JLPT_WEIGHT = 100` (validated). Do not change without re-running ranking tests.
- Entry search is one SQL query for reading and gloss matches, ranked by `score = match_tier × 2000 + popularity`, with gloss popularity decayed by the matched sense's position (`/ log2(pos + 2)`). See `docs/technical/search.md`.

## Development conventions

- General Python backend conventions (how to layer, name, type, persist, test) are in
  the `python-backend-clean-code` skill. The specifics of this repo are below and in
  each package's own `CLAUDE.md` (`packages/shodoukan-practice/CLAUDE.md`).
- Git, documentation, and changelog conventions (repo-wide, not just Python) are in
  `.claude/rules/git-and-docs.md`.
- Documentation subagents (`.claude/agents/`): `docs-explorer` (read-only) finds and
  summarises what the docs say about an area before working on it; `docs-maintainer`
  updates the docs, indexes and `CHANGELOG.md` to match a change (edits Markdown only,
  never commits). `architecture-reviewer` (read-only) checks a backend plan before
  coding, and the implemented change before the PR, against the clean architecture
  rules and `decisions.md`; structural coherence only, not QA.
- Frontend work on `packages/shodoukan-practice-web` (Nuxt UI v4) loads the `nuxt-ui`
  skill (`.claude/skills/nuxt-ui/`, the official Nuxt UI skill; update it with
  `npx skills update nuxt-ui`, pinned in `skills-lock.json`).

### Python tooling in this repo

- **Ruff:** `ruff.toml` at the repo root (`line-length = 88`, rules
  `E,W,F,I,UP,B,C4,SIM,RUF`). Add every new first-party package to
  `[lint.isort] known-first-party`.
- **mypy:** `mypy.ini` at the repo root, with the `pydantic.mypy` plugin. Run `mypy`
  from the root; it checks the paths under `files` (today `shodoukan-practice` and its
  tests, `strict = True`). The developer also runs it through the VS Code mypy
  extension (`.vscode/settings.json` points it at `mypy.ini` and `.venv`). CI runs it
  too.
- **Checks before a change is done:** `ruff check`, `ruff format`, `mypy`, and the
  package's tests. Existing Ruff findings in `shodoukan` / `shodoukan-api` predate this
  and aren't part of CI.
- All backend packages are synchronous today; agree with the developer before
  introducing async.

### Legacy packages (don't retrofit)

`packages/shodoukan` (core library) and `packages/shodoukan-api` predate the layering
and naming conventions. They're pragmatic, read-only and not under mypy. Follow the
conventions in new code only; don't rename or restructure these packages wholesale.

- Core layout: `models/entry.py` (domain models), `db/orm.py` (ORM),
  `repositories/mapper.py` (`entry_to_domain`, read-only mappers), concrete
  repositories with no interface.
- API wiring example: `packages/shodoukan-api/src/shodoukan_api/deps.py`
  (`dictionary_dep`).
- Tests: `tests/db_helpers.py` (schema + seed data) and `tests/shodoukan/conftest.py`
  (`conn` fixture on `sqlite3.connect(":memory:")`, `engine` via
  `open_test_connection` with `StaticPool`). Example: `tests/shodoukan/test_entry_repository.py`.

### shodoukan-practice

Follows the skill's conventions fully. Its specifics (layout, database, migrations,
tests, docs) are in `packages/shodoukan-practice/CLAUDE.md`.

**Its docs are written on the fly:** any change that adds or alters architecture,
entities, ports, schema, migrations, config or conventions updates the matching page
under `docs/practice/technical/` in the same commit. The "where to document what" table
in `docs/practice/technical/README.md` maps code areas to pages; non-obvious choices
get an entry in `decisions.md`. Functional docs (`docs/practice/functional/<feature>/`)
are added once a feature's use cases are defined.
