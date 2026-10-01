# Configuration and Local Setup

[← Technical documentation](../README.md)

Environment variables, the local PostgreSQL, and how the app connects.

## Environment variables

| Variable | Used by | Description |
|---|---|---|
| `PRACTICE_DATABASE_URL` | app, Alembic | SQLAlchemy URL, e.g. `postgresql+psycopg://user:pass@localhost:5432/shodoukan_practice`. **Required.** There's no default, so credentials never live in code. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | `practice-db` container | Must match the URL. |
| `AUTH_ISSUER` | API | **Required to serve requests.** Keycloak realm URL, e.g. `https://keycloak.example/realms/shodoukan`; tokens must carry it as `iss`. |
| `AUTH_AUDIENCE` | API | Optional. When set, tokens must carry it in `aud` (needs a Keycloak audience mapper). |
| `AUTH_JWKS_URL` | API | Optional. Defaults to `<AUTH_ISSUER>/protocol/openid-connect/certs`. |
| `SHODOUKAN_DB_PATH` | dictionary (`shodoukan` library) | Optional. Path to the dictionary SQLite; defaults to `~/.local/share/shodoukan/shodoukan.sqlite`. |

Real values live in the gitignored `.env.dev` (local) or the deployment's secret
settings. [`.env.example`](../../../../.env.example) documents every variable with
placeholder values.

## Local PostgreSQL

`docker-compose.yml` defines `practice-db`:

- `postgres:16-alpine`, credentials from `.env.dev`;
- bound to `127.0.0.1:${PRACTICE_DB_PORT:-5432}` only;
- data in the named volume `practice-db-data`;
- a `pg_isready` healthcheck, so a future API service can wait for it with
  `depends_on: condition: service_healthy`.

```bash
docker compose up -d practice-db
set -a; . ./.env.dev; set +a
alembic -c packages/shodoukan-practice/alembic.ini upgrade head
docker compose stop practice-db     # when done
```

## Dictionary database

The practice app reads the shodoukan dictionary in-process (see the
[dictionary gateway](../infrastructure/dictionary-gateway.md)), so it needs the
dictionary SQLite on disk:

- **Locally:** `shodoukan-setup` downloads it to the default path, or set
  `SHODOUKAN_DB_PATH`. `Dictionary()` also downloads it on first use if it's missing.
- **In a deployment:** download it at image build time with `shodoukan-setup`, as
  `packages/shodoukan-api/Dockerfile` does, or mount it. There's no practice
  Dockerfile yet.

The file is read-only and published monthly by `shodoukan-db`. Imported items are
snapshots, so a dictionary update never changes what users already have.

## Connection (`infrastructure/db/connection.py`)

| Function | Does |
|---|---|
| `database_url()` | Reads `PRACTICE_DATABASE_URL`; raises `RuntimeError` if it's missing |
| `create_db_engine(url=None)` | Engine with `pool_pre_ping=True` |
| `create_session_factory(engine)` | `sessionmaker` with `expire_on_commit=False` |

The module only reads the process environment. Loading env files is the launcher's
job (shell `set -a`, VS Code `envFile`, the container's `env_file`).

## Dependencies

Runtime: SQLAlchemy 2, Alembic, psycopg 3 (binary), Pydantic 2, FastAPI.
Dev: pytest, ruff, mypy (with the Pydantic plugin). Declared in
[`packages/shodoukan-practice/pyproject.toml`](../../../../packages/shodoukan-practice/pyproject.toml).
