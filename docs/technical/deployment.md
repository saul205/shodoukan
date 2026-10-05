# Deployment

[← Documentation index](../index.md)

How shodoukan is deployed, at no cost and without a card or a paid domain. It
covers the environments, the first-time setup and day-to-day operations. The
reasons behind these choices are in [decisions](../practice/technical/decisions.md#deployment-split-dictionary-on-render-practice-self-hosted).

## Topology

| Part | Where | Deployed by |
|---|---|---|
| Dictionary API (`shodoukan-api`) | Render web service (free), Docker image `packages/shodoukan-api/Dockerfile` | CI → Render deploy hook on every push to `main` |
| Dictionary web (`shodoukan-web`) | Render Static Site (free), a static SPA (`nuxt generate`) | CI → Render deploy hook on every push to `main` |
| Practice stack: API, PostgreSQL, Keycloak + its PostgreSQL, practice SPA | A machine of ours, `docker compose`, published with **Tailscale Funnel** | CI publishes images to GHCR; `deploy/deploy.sh` on the host |

The two halves are independent. The practice API reads the dictionary in-process from
its own baked-in copy, so it never calls Render (see [the dictionary gateway decision](../practice/technical/decisions.md#the-dictionary-is-used-in-process-behind-a-port)).

### The practice stack

Funnel gives one HTTPS hostname, `https://shodoukan.<tailnet>.ts.net`, and Caddy (the
`web` service) routes by path:

| Path | Service | Notes |
|---|---|---|
| `/` | practice SPA, static files | `try_files … /index.html` for client-side routes |
| `/practice-api/*` | `practice-api` (uvicorn :8001) | `UVICORN_ROOT_PATH=/practice-api`, so `/practice-api/docs` works |
| `/idp/*` | `keycloak` (:8080) | built with `http-relative-path=/idp` |
| `/idp/admin*`, `/idp/realms/master*` | blocked (404) | the admin console is only on `localhost` (see [Keycloak admin](#keycloak-admin)) |

Everything is same-origin, so the browser never needs CORS. The SPA is built once with
relative URLs (`/practice-api`, `/idp/realms/shodoukan`), so the same image serves pre
and prod.

```
 browser ──HTTPS──▶ Tailscale Funnel ──▶ tailscale ──▶ web (Caddy :80)
                                                       ├── /               SPA files
                                                       ├── /practice-api/  practice-api ──▶ practice-db
                                                       └── /idp/           keycloak ──────▶ keycloak-db
 practice-api ──(JWKS, internal)──▶ keycloak
 practice-db-backup, keycloak-db-backup ──▶ volumes practice-backups, keycloak-backups (nightly)
```

Files:

| Path | What |
|---|---|
| `deploy/compose.yml` | The shared stack. Publishes no ports. |
| `deploy/compose.pre.yml` | Pre: builds from the working tree, web on `127.0.0.1:8088`, project `shodoukan-pre` |
| `deploy/compose.prod.yml` | Prod: GHCR images (`TAG`), adds `tailscale`, project `shodoukan-prod` |
| `deploy/Caddyfile`, `deploy/web/Dockerfile` | Caddy routing; the image that bundles Caddy and the SPA |
| `deploy/tailscale/serve.json` | Funnel: port 443 → `http://web:80` |
| `deploy/pre.sh`, `deploy/deploy.sh`, `deploy/lib.sh` | Helper scripts (use these, not raw compose) |
| `deploy/.env.pre.example`, `deploy/.env.prod.example` | Every variable, documented |
| `packages/shodoukan-practice/Dockerfile` | Practice API image. It also runs the migrations. |
| `docker/keycloak/Dockerfile`, `docker/keycloak/prod/realm-shodoukan.json` | Optimized Keycloak and the deployed realm |

## Environments

| | Dev | Pre | Prod |
|---|---|---|---|
| What | Code with hot reload | The prod stack, built locally | The real thing |
| Compose | `docker-compose.yml` (DBs + Keycloak `start-dev`) | `deploy/compose.yml` + `compose.pre.yml` | `deploy/compose.yml` + `compose.prod.yml` |
| Project / volumes | `shodoukan` | `shodoukan-pre` | `shodoukan-prod` |
| URL | API :8001, SPA :3001, Keycloak :8080 | `http://localhost:8088` | `https://shodoukan.<tailnet>.ts.net` |
| Realm | dev realm (`dev`/`dev`, dev CLI client) | prod realm | prod realm |
| Env file | `.env.dev`, `.env.keycloak` | `deploy/.env.pre` | `deploy/.env.prod` |

All three can run side by side on one machine: pre and prod publish no ports that
clash with dev. Each has its **own databases**. Pre never reuses the dev ones,
because:

- its migrations would change dev data;
- Keycloak only imports a realm that doesn't exist yet, so pre would keep the dev
  realm instead of testing the prod one;
- a different `KC_HOSTNAME` changes the token issuer and would break dev sign-in.

## Variables

The compose files read these from the `--env-file` (`deploy/.env.pre` or
`deploy/.env.prod`), and the services get them as environment:

| Variable | Used for |
|---|---|
| `PUBLIC_URL` | The browser's URL for the stack. Sets the tokens' issuer (`AUTH_ISSUER`), Keycloak's `KC_HOSTNAME` (`<url>/idp`), `CORS_ORIGINS` and the realm's redirect URIs. |
| `PUBLIC_SCHEME` | `https` in prod, `http` in pre. Caddy passes it to Keycloak as `X-Forwarded-Proto`. |
| `PRACTICE_DB_USER`, `PRACTICE_DB_PASSWORD`, `PRACTICE_DB_NAME` | The practice database and `PRACTICE_DATABASE_URL`. The password goes into a URL, so use letters and digits. |
| `KEYCLOAK_DB_USER`, `KEYCLOAK_DB_PASSWORD` | Keycloak's database |
| `KEYCLOAK_ADMIN_USER`, `KEYCLOAK_ADMIN_PASSWORD` | Keycloak's first admin (bootstrap) |
| `KEYCLOAK_ADMIN_PORT` | Localhost port of the admin console: `8180` in prod, `8181` in pre |
| `WEB_PORT` | Pre only: the host port for Caddy (`8088`) |
| `TS_AUTHKEY` | Prod only: Tailscale auth key for the first login |
| `TAG` | Prod only: the image tag. `deploy.sh` sets it. |

The practice API's own variables (`AUTH_*`, `UVICORN_ROOT_PATH`, …) are derived from
these in `deploy/compose.yml`, so the env files never set them directly. They're
described in [configuration](../practice/technical/cross-cutting/configuration.md).
`AUTH_JWKS_URL` points at Keycloak inside the Docker network, so fetching the
signing keys doesn't go out through Funnel.

## Pre

```bash
cp deploy/.env.pre.example deploy/.env.pre   # once
deploy/pre.sh up       # build from the working tree and start; waits for the smoke test
deploy/pre.sh down     # stop (data kept, nothing running)
deploy/pre.sh reset    # delete pre's data: the next up migrates from zero and imports the realm
deploy/pre.sh seed     # copy the dev practice DB into pre and migrate it (tests a migration on real data)
deploy/pre.sh logs practice-api   # or any compose command
```

Then open `http://localhost:8088`, register a user, and go through the app. The
realm has no seeded users. Seeded data belongs to dev-realm users, so after `seed`
you sign in as a new user. Run pre before merging anything that touches the
Dockerfiles, the compose files, the realm or a migration.

## Prod: first-time setup

On the host (today the developer's PC under WSL2; a spare Linux machine works the
same way):

1. **Docker Engine.** Use Docker Engine inside the distro, not Docker Desktop. If
   Docker Desktop is installed, turn its WSL integration off (Settings → Resources →
   WSL integration). Otherwise it replaces `/var/run/docker.sock` and its
   `/usr/local/lib/docker/cli-plugins` links can hide `compose` and `buildx`.
2. **WSL limits and uptime** (Windows only):
   - Cap the VM in `%UserProfile%\.wslconfig`:
     ```ini
     [wsl2]
     memory=4GB
     processors=2
     ```
   - WSL stops a distro when nothing holds it open. Add a Windows Task Scheduler task
     "At log on" that runs `wsl.exe -d Ubuntu -- sleep infinity`, so the stack keeps
     running while you're logged in.
3. **Tailscale** (free, sign in with GitHub, no card):
   - Create the account. In the admin console, enable **MagicDNS** and **HTTPS
     certificates** (DNS page), and allow **Funnel** in the access controls: add the
     `funnel` node attribute. The console offers it the first time.
   - Create an auth key (Settings → Keys).
   - The node registers as `shodoukan`, so the URL is
     `https://shodoukan.<tailnet>.ts.net`. Disable key expiry for that node in the
     Machines page.
4. **Env file:** `cp deploy/.env.prod.example deploy/.env.prod`, then set:
   - `PUBLIC_URL` to the Funnel URL;
   - long random passwords;
   - `TS_AUTHKEY`.
5. **Images:** the first run of the "Publish practice images" workflow creates three
   GHCR packages, and they start out private. Make each one public: GitHub → your
   profile → Packages → package → Package settings → Change visibility. Then
   `docker pull` needs no login. The alternative is
   `docker login ghcr.io` with a token that has the `read:packages` scope.
6. **Deploy:** `deploy/deploy.sh`.
   - Check the URL from a phone on mobile data. That proves Funnel is really
     public.
   - After the first login the node state is kept in the `tailscale-state` volume,
     so you can clear `TS_AUTHKEY`.

## Prod: operations

### Deploy and roll back

A merge to `main` triggers two things:

- CI deploys the dictionary to Render.
- Once CI passes, `practice-publish.yml` pushes `shodoukan-practice-api`,
  `shodoukan-practice-web` and `shodoukan-keycloak` to GHCR, tagged `latest` and with
  the 7-character commit SHA.

Then, on the host:

```bash
git pull                     # deploy/ files (compose, Caddyfile) come from the checkout
deploy/deploy.sh             # pull latest, migrate, restart, smoke test
deploy/deploy.sh 1a2b3c4     # deploy (or roll back to) a commit's images
deploy/deploy.sh logs keycloak
deploy/deploy.sh ps
```

`deploy.sh` pulls the images and runs `up -d`. `practice-migrate` runs
`alembic upgrade head` before `practice-api` starts. The script then waits until `/`,
`/practice-api/health` and `/idp/realms/shodoukan` answer.

Migrations are append-only and never run backwards. Rolling the images back past a
migration leaves a newer schema under older code: restore a backup taken before the
upgrade instead.

### Monthly dictionary refresh

`shodoukan-db` publishes a new dictionary at the start of each month. On the 2nd:

- `scheduled.yml` redeploys the Render API, whose image build downloads the latest
  release.
- `practice-publish.yml` rebuilds the practice images. Run `deploy/deploy.sh` on the
  host afterwards to pick them up.

Imported library items are snapshots, so a refresh never changes users' data.

### Keep-alive

The free Render web service sleeps after 15 minutes without traffic, and waking it
takes 30–60 s. `scheduled.yml` pings `$DICT_API_URL/health` every 10 minutes. One
always-on service uses about 744 of the 750 free instance hours a month, so **don't
add a second free web service**: the static site uses no instance hours. GitHub pauses
scheduled workflows after 60 days without repository activity. Re-enable it from the
Actions tab, or use an external pinger such as cron-job.org (free, no card).

### Backups

`practice-db-backup` and `keycloak-db-backup` dump each database nightly into their
own volume (`practice-backups`, `keycloak-backups`), with 7 daily and 4 weekly dumps
kept. Each volume has `last/`, `daily/`, `weekly/` and `monthly/` folders, and
`last/<db>-latest.sql.gz` points at the newest dump.

```bash
# Take one now
deploy/deploy.sh exec practice-db-backup /backup.sh
# Copy the dumps off the machine (e.g. to Windows)
docker run --rm -v shodoukan-prod_practice-backups:/backups:ro \
  -v /mnt/c/Users/<you>/shodoukan-backups:/out alpine cp -rL /backups/. /out/practice/
# Restore the practice DB from the latest dump into an empty schema
set -a; . deploy/.env.prod; set +a
deploy/deploy.sh stop practice-api
deploy/deploy.sh exec -T practice-db psql -U "$PRACTICE_DB_USER" -d "$PRACTICE_DB_NAME" \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
deploy/deploy.sh exec -T practice-db-backup cat /backups/last/shodoukan_practice-latest.sql.gz \
  | gunzip | deploy/deploy.sh exec -T practice-db psql -q -U "$PRACTICE_DB_USER" -d "$PRACTICE_DB_NAME"
deploy/deploy.sh start practice-api
```

Keycloak's database restores the same way: use `keycloak-db-backup`, the `keycloak`
database and `KEYCLOAK_DB_USER`, with Keycloak stopped. In pre, use `deploy/pre.sh`
and the `shodoukan-pre_*` volumes.

### Keycloak admin

The admin console and the master realm are never public: Caddy answers 404 for them.
Keycloak's `KC_HOSTNAME_ADMIN` puts the console on this machine only:

- prod: `http://localhost:8180/idp/admin`
- pre: `http://localhost:8181/idp/admin`

Sign in with `KEYCLOAK_ADMIN_USER` / `KEYCLOAK_ADMIN_PASSWORD`. After the first login,
create a permanent admin user and delete the bootstrap one.

The realm file (`docker/keycloak/prod/realm-shodoukan.json`) is imported only when the
realm doesn't exist yet. Later changes to the file don't reach a running prod realm:
apply them in the console, or with `kcadm.sh` as in
[configuration](../practice/technical/cross-cutting/configuration.md#keycloak).

### Moving to another machine

1. On the old host, take backups (above) and run `deploy/deploy.sh down`.
2. Remove the old `shodoukan` node in the Tailscale admin console, so the new one gets
   the same name and URL.
3. On the new host:
   - Install Docker Engine.
   - Clone the repo and copy `deploy/.env.prod`, with a new `TS_AUTHKEY`.
   - Run `deploy/deploy.sh`, then restore the dumps.
4. The images are amd64. For an ARM device such as a Raspberry Pi, add
   `platforms: linux/amd64,linux/arm64` to `practice-publish.yml`.

## Render

### Dictionary API (web service)

This already exists.

- Settings:
  - Docker, root directory: the repository root.
  - Dockerfile path: `packages/shodoukan-api/Dockerfile`.
  - **Auto-Deploy off**: CI deploys it.
- Environment:
  - `CORS_ORIGINS` = the static site's URL.
  - `SHODOUKAN_DEBUG=0`.
- Deploy hook → GitHub secret `RENDER_HOOK_DICT_API`.
- Its public URL (without a trailing slash) → GitHub **variable** `DICT_API_URL`, used
  by the keep-alive.

### Dictionary web (static site)

To create it: New → Static Site, from this repository.

| Setting | Value |
|---|---|
| Build command | `corepack enable && pnpm install --frozen-lockfile && pnpm --filter shodoukan-ui build && pnpm --filter shodoukan-web generate` |
| Publish directory | `packages/shodoukan-web/.output/public` |
| Environment | `NUXT_PUBLIC_API_BASE` = the API's URL (read at build time), `NODE_VERSION=22` |
| Redirects/Rewrites | Rewrite `/*` → `/index.html` (client-side routes such as `/entry/123`) |
| Auto-Deploy | Off. CI deploys it. |

Its deploy hook → GitHub secret `RENDER_HOOK_DICT_WEB`. Until that secret exists, CI
skips this step.

## CI/CD summary

| Workflow | When | Does |
|---|---|---|
| `ci.yml` | push / PR to `main` or `develop` | Backend tests and migrations; frontend tests and builds; builds all four images (no push). On `main` pushes, triggers the two Render deploy hooks. |
| `practice-publish.yml` | CI passed on `main`; the 2nd of each month; manually | Builds and pushes the three practice images to GHCR |
| `scheduled.yml` | Every 10 min; the 2nd of each month | Pings the Render API; redeploys it monthly |

Secrets: `RENDER_HOOK_DICT_API`, `RENDER_HOOK_DICT_WEB`. Variable: `DICT_API_URL`.
`GITHUB_TOKEN` is used for GHCR and for the release lookup in `shodoukan-setup`.
Nothing from GitHub runs on the practice host.
