# Configuration and Local Setup

[← Technical documentation](../README.md)

Environment variables, the local PostgreSQL, and how the app connects.

## Environment variables

| Variable | Used by | Description |
|---|---|---|
| `PRACTICE_DATABASE_URL` | app, Alembic | SQLAlchemy URL, e.g. `postgresql+psycopg://user:pass@localhost:5432/shodoukan_practice`. **Required.** There's no default, so credentials never live in code. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | `practice-db` container | Must match the URL. |
| `AUTH_ISSUER` | API | **Required to serve requests.** Realm URL; locally `http://localhost:8080/realms/shodoukan`. Tokens must carry it as `iss`. |
| `AUTH_AUDIENCE` | API | Recommended. Tokens must carry it in `aud`; locally `shodoukan-practice`. |
| `AUTH_JWKS_URL` | API | Optional. Defaults to `<AUTH_ISSUER>/protocol/openid-connect/certs`. |
| `CORS_ORIGINS` | API | Comma-separated browser origins allowed to call the API; default `http://localhost:3001` (the practice frontend). Shared with `shodoukan-api`, so a value covering both apps lists both origins. |
| `AUTH_SWAGGER_CLIENT_ID` | API docs | Optional. Client the Swagger UI signs in with; default `shodoukan-web` (deployed: `shodoukan-practice-docs`). |
| `UVICORN_ROOT_PATH` | API container | The path prefix the proxy strips (`/practice-api` when deployed), so the docs and OpenAPI URLs include it. Read by uvicorn. |
| `KEYCLOAK_PORT` | compose | Optional host port for Keycloak; default `8080`. Changing it also changes the issuer URL. |
| `NUXT_PUBLIC_API_BASE`, `NUXT_PUBLIC_AUTH_ISSUER`, `NUXT_PUBLIC_AUTH_CLIENT_ID` | practice frontend | Optional; defaults match the local setup. See [frontend](../frontend.md#running). |
| `SHODOUKAN_DB_PATH` | dictionary (`shodoukan` library) | Optional. Path to the dictionary SQLite; defaults to `~/.local/share/shodoukan/shodoukan.sqlite`. |

Real values live in the gitignored `.env.dev` (local). Deployed (pre),
`deploy/compose.yml` derives the API's variables from a few in `deploy/.env.pre`; see [deployment](../../../technical/deployment.md#variables-deployenvpre). Keycloak and its database have their own file; see [Keycloak](#keycloak). [`.env.example`](../../../../.env.example) documents every variable with
placeholder values.

## Local PostgreSQL

`docker-compose.yml` defines `practice-db`:

- `postgres:16-alpine`, credentials from `.env.dev`;
- bound to `127.0.0.1:${PRACTICE_DB_PORT:-5432}` only;
- data in the named volume `practice-db-data`;
- a `pg_isready` healthcheck, so a future API service can wait for it with
  `depends_on: condition: service_healthy`.

```bash
docker compose up -d practice-db keycloak
set -a; . ./.env.dev; set +a
alembic -c packages/shodoukan-practice/alembic.ini upgrade head
uvicorn shodoukan_practice.api.app:app --port 8001 --reload   # docs: http://localhost:8001/docs
docker compose stop keycloak practice-db                       # when done
```

In VS Code, the **Practice API** launch configuration does the same with the debugger
attached. Its `practice: prepare` task starts `practice-db` and `keycloak` (waiting
until they're healthy), applies the migrations, and then runs uvicorn on port 8001
with `.env.dev` loaded.

## Authentication

The API verifies Keycloak access tokens (see [authentication](../api/authentication.md)).
Locally, `.env.dev` sets `AUTH_ISSUER=http://localhost:8080/realms/shodoukan` and
`AUTH_AUDIENCE=shodoukan-practice`. `TokenVerifier.from_env()` raises at the first
authenticated request if `AUTH_ISSUER` is missing.

## Keycloak

Two compose services, independent of the practice API and its database:

| Service | Image | Role |
|---|---|---|
| `keycloak-db` | `postgres:16-alpine` | Keycloak's own database. Starts empty and Keycloak creates its tables on first start; no init scripts. Not exposed to the host. Volume `keycloak-db-data`. |
| `keycloak` | `quay.io/keycloak/keycloak:26.3` | `start-dev --import-realm`, on `127.0.0.1:${KEYCLOAK_PORT:-8080}`. Waits for `keycloak-db`; health check on the management port (`9000/health/ready`). |

- `KC_HOSTNAME=http://localhost:8080`, so tokens are issued as
  `http://localhost:8080/realms/shodoukan` for both the browser and the API on the
  host.
- It imports `docker/keycloak/realm-shodoukan.json` on start, but only if the realm
  doesn't exist yet.
- The two databases are separate servers: Keycloak never touches the practice tables,
  and the practice app only knows Keycloak through tokens (`sub` = `users.id`).

### `.env.keycloak`

Both services read the gitignored `.env.keycloak`; copy it from
[`.env.keycloak.example`](../../../../.env.keycloak.example). It's separate from
`.env.dev` because `keycloak-db` needs `POSTGRES_*` variables, the same names
`practice-db` uses. Keycloak's connection values reference the database ones
(Compose interpolates `${...}` inside env files), so each value is written once:

| Variable | Read by | Description |
|---|---|---|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | `keycloak-db` | Database and owner created on first start |
| `KC_DB_URL_DATABASE`, `KC_DB_USERNAME`, `KC_DB_PASSWORD` | `keycloak` | `${POSTGRES_DB}`, `${POSTGRES_USER}`, `${POSTGRES_PASSWORD}` |
| `KC_BOOTSTRAP_ADMIN_USERNAME`, `KC_BOOTSTRAP_ADMIN_PASSWORD` | `keycloak` | First admin of the console (`http://localhost:8080/admin`) |

```bash
cp .env.keycloak.example .env.keycloak   # then set real passwords
docker compose up -d keycloak            # starts keycloak-db first
```

To re-import the realm after editing `realm-shodoukan.json`, either reset Keycloak's
data (`docker compose rm -sf keycloak keycloak-db && docker volume rm
shodoukan_keycloak-db-data`), or delete just the realm and restart:

```bash
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD"
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh delete realms/shodoukan
docker compose restart keycloak
```

Either way the realm's users are recreated with new `sub`s, so existing practice users
won't match them any more. Do it only on throwaway local data.

To add a **new client** to an existing realm without losing its users, create just that
client from the file (here `shodoukan-practice-web`):

```bash
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD"
python -c "import json; print(json.dumps(next(c for c in json.load(open('docker/keycloak/realm-shodoukan.json'))['clients'] if c['clientId'] == 'shodoukan-practice-web')))" \
  | docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh create clients -r shodoukan -f -
```

## Dictionary database

The practice app reads the shodoukan dictionary in-process (see the
[dictionary gateway](../infrastructure/dictionary-gateway.md)), so it needs the
dictionary SQLite on disk:

- **Locally:** `shodoukan-setup` downloads it to the default path, or set
  `SHODOUKAN_DB_PATH`. `Dictionary()` also downloads it on first use if it's missing.
- **Deployed:** `packages/shodoukan-practice/Dockerfile` downloads it in its own
  build stage, from the `shodoukan-db` release named by the `DICT_RELEASE` build arg
  (default `latest`), and sets `SHODOUKAN_DB_PATH`. The stage is cached per release,
  so code changes don't download it again; `deploy/deploy.sh` passes the latest release
  ([deployment](../../../technical/deployment.md#monthly-dictionary-refresh)).
  `shodoukan-setup` (used by the `shodoukan-api` image and locally) sends
  `GITHUB_TOKEN`, when set, to avoid GitHub's anonymous rate limit.

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
