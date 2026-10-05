# Deployment

[← Documentation index](../index.md)

How shodoukan is deployed, at no cost and without a card or a paid domain. It
covers the environments, the first-time setup and day-to-day operations. The
reasons behind these choices are in [decisions](../practice/technical/decisions.md#one-pre-environment-shared-through-a-private-tailscale-tunnel).

## Topology

| Part | Where | Deployed by |
|---|---|---|
| Dictionary API (`shodoukan-api`) | Render web service (free), Docker image `packages/shodoukan-api/Dockerfile` | CI → Render deploy hook on every push to `main` |
| Dictionary web (`shodoukan-web`) | Render Static Site (free), a static SPA (`nuxt generate`) | CI → Render deploy hook on every push to `main` |
| Practice stack: API, PostgreSQL, Keycloak + its PostgreSQL, practice SPA | **Pre**, on the developer's machine with `docker compose`, shared privately through **Tailscale** | `deploy/deploy.sh` on that machine, built from `main` |

The two halves are independent. The practice API reads the dictionary in-process from
its own baked-in copy, so it never calls Render (see [the dictionary gateway decision](../practice/technical/decisions.md#the-dictionary-is-used-in-process-behind-a-port)).

### Pre

Pre is the one self-hosted environment: friends use it, so its data matters. It isn't
public. The `tailscale` container serves it as `https://shodoukan.<tailnet>.ts.net` on
our tailnet, and only our devices and the people we share the node with can reach it.
Caddy (the `web` service) routes by path:

| Path | Service | Notes |
|---|---|---|
| `/` | practice SPA, static files | `try_files … /index.html` for client-side routes |
| `/practice-api/*` | `practice-api` (uvicorn :8001) | Caddy strips the prefix; `UVICORN_ROOT_PATH=/practice-api` keeps it in the docs and OpenAPI URLs |
| `/idp/*` | `keycloak` (:8080) | built with `http-relative-path=/idp` |
| `/idp/admin*`, `/idp/realms/master*` | blocked (404) | the admin console is only on `localhost` (see [Keycloak admin](#keycloak-admin)) |

Everything is same-origin, so the browser never needs CORS. The SPA is built with
relative URLs (`/practice-api`, `/idp/realms/shodoukan`), so the same build works on
any host.

```
 friend's device ──Tailscale──▶ tailscale (node "shodoukan", HTTPS) ──▶ web (Caddy :80)
                                                                         ├── /               SPA files
                                                                         ├── /practice-api/  practice-api ──▶ practice-db
                                                                         └── /idp/           keycloak ──────▶ keycloak-db
 practice-api ──(JWKS, internal)──▶ keycloak
 keycloak-setup (one-shot): invite-only realm, client URLs, admin sign-in on localhost
 practice-db-backup, keycloak-db-backup ──▶ volumes practice-backups, keycloak-backups (nightly)
```

| Path | What |
|---|---|
| `deploy/compose.yml` | The whole stack, in one file. Project `shodoukan-pre`. Its `tailscale` service only runs with the `tunnel` profile. |
| `deploy/deploy.sh` | Deploy, back up, seed, and run any compose command. Always use it rather than raw compose. |
| `deploy/.env.pre.example` | Every variable, documented. The real file, `deploy/.env.pre`, is gitignored. |
| `deploy/Caddyfile`, `deploy/web/Dockerfile` | Caddy's routing, and the image that bundles Caddy with the generated SPA |
| `deploy/tailscale/serve.json` | `tailscale serve`: HTTPS on 443 → `http://web:80`, tailnet only (no Funnel) |
| `packages/shodoukan-practice/Dockerfile` | Practice API image. It also runs the migrations. |
| `docker/keycloak/Dockerfile`, `docker/keycloak/prod/realm-shodoukan.json`, `docker/keycloak/setup.sh` | Optimized Keycloak, the deployed realm, and the script `keycloak-setup` runs |

## Environments

| | Dev | Pre |
|---|---|---|
| What | Code with hot reload | The stack friends use |
| Runs | Your working tree | A commit, by default `origin/main`, built in a separate worktree |
| Compose | `docker-compose.yml` (DBs + Keycloak `start-dev`) | `deploy/compose.yml` |
| Project / volumes | `shodoukan` | `shodoukan-pre` |
| URL | API :8001, SPA :3001, Keycloak :8080 | `PUBLIC_URL`, and `http://localhost:8088` from this machine |
| Realm | dev realm (`dev`/`dev`, dev CLI client, open registration) | deployed realm (invite-only) |
| Env file | `.env.dev`, `.env.keycloak` | `deploy/.env.pre` |

Both run side by side. Pre has **its own databases**. Try risky changes in dev: a
migration lands on pre's data, so test it there first, or on a copy (`seed` below).
`deploy.sh` takes a backup before every deploy, so a bad one can be restored.

## Variables (`deploy/.env.pre`)

| Variable | Used for |
|---|---|
| `PUBLIC_URL` | The URL people use. It sets the tokens' issuer (`AUTH_ISSUER`), Keycloak's `KC_HOSTNAME` (`<url>/idp`), `CORS_ORIGINS` and the clients' redirect URIs (kept in sync by `keycloak-setup`). Sign-in only works on this URL. |
| `PUBLIC_SCHEME` | `https` with the tunnel, `http` on localhost. Caddy passes it to Keycloak as `X-Forwarded-Proto`. |
| `COMPOSE_PROFILES` | `tunnel` to run the `tailscale` service; empty for localhost only |
| `WEB_PORT` | Caddy on `127.0.0.1` (default `8088`), for checks from this machine |
| `TS_AUTHKEY` | Tailscale auth key, only needed for the node's first login |
| `PRACTICE_DB_USER`, `PRACTICE_DB_PASSWORD`, `PRACTICE_DB_NAME` | The practice database and `PRACTICE_DATABASE_URL`. The password goes into a URL, so use letters and digits. |
| `KEYCLOAK_DB_USER`, `KEYCLOAK_DB_PASSWORD` | Keycloak's database |
| `KEYCLOAK_ADMIN_USER`, `KEYCLOAK_ADMIN_PASSWORD` | Keycloak's admin. `keycloak-setup` signs in with it on every start, so keep this user. |
| `KEYCLOAK_ADMIN_PORT` | Localhost port of the admin console (default `8181`) |
| `SEED_USERS` | Default users for `deploy.sh seed` |

Database passwords only take effect when a volume is first created. See
[changing passwords](#changing-passwords).

The practice API's own variables (`AUTH_*`, `UVICORN_ROOT_PATH`, …) are derived from
these in `deploy/compose.yml`, so `.env.pre` never sets them directly. They're described
in [configuration](../practice/technical/cross-cutting/configuration.md). `AUTH_JWKS_URL`
points at Keycloak inside the Docker network, so fetching the signing keys doesn't go
out through the tunnel. `deploy.sh` sets two more itself: `TAG`, the deployed commit's
short SHA, which tags the images; and `DICT_RELEASE`, the latest `shodoukan-db`
release.

## First-time setup

On the host (today the developer's PC under WSL2; any Linux machine with Docker works
the same way):

1. **Docker Engine.** Use Docker Engine inside the distro, not Docker Desktop. If
   Docker Desktop is installed, turn its WSL integration off (Settings → Resources →
   WSL integration). Otherwise it replaces `/var/run/docker.sock`, and its
   `/usr/local/lib/docker/cli-plugins` links can hide `compose` and `buildx`.
2. **WSL limits and uptime** (Windows only):
   - Cap the VM in `%UserProfile%\.wslconfig`:
     ```ini
     [wsl2]
     memory=4GB
     processors=2
     ```
   - WSL stops a distro when nothing holds it open. Add a Windows Task Scheduler task
     "At log on" that runs `wsl.exe -d Ubuntu -- sleep infinity`, so pre keeps running
     while you're logged in.
3. **Env file:** `cp deploy/.env.pre.example deploy/.env.pre` and set the passwords.
   Use `PUBLIC_URL=http://localhost:8088` until the tunnel is ready.
4. **First deploy:** `deploy/deploy.sh`. Check it on `http://localhost:8088`.
5. **Tailscale** (free, sign in with Google, Microsoft, Apple or GitHub, no card):
   - Create the account and install Tailscale on your own devices. Pre is only
     reachable from devices on the tailnet.
   - In the admin console, enable **MagicDNS** and **HTTPS certificates** (DNS page).
     Don't enable Funnel: pre must not be public.
   - Create an auth key (Settings → Keys).
   - In `deploy/.env.pre`, set:
     - `COMPOSE_PROFILES=tunnel` and `TS_AUTHKEY`;
     - `PUBLIC_URL=https://shodoukan.<tailnet>.ts.net` (the tailnet name is on the DNS
       page) and `PUBLIC_SCHEME=https`.
   - Run `deploy/deploy.sh`. The node registers as `shodoukan`. In the Machines page,
     disable key expiry for it. Its state is kept in the `tailscale-state` volume, so
     `TS_AUTHKEY` can be cleared afterwards.
6. **Your account:** create it in the admin console (see [Inviting people](#inviting-people)),
   or copy your dev user with `deploy/deploy.sh seed <username>`.

## Inviting people

Two steps per person, both reversible:

1. **Network access.** In the Tailscale admin console, open Machines → `shodoukan` →
   Share, and send the invite link to their email.
   - They install Tailscale on their phone (iOS/Android) or computer, sign in with
     their own free account, and accept the invite.
   - While Tailscale is on, `https://shodoukan.<tailnet>.ts.net` opens in any browser.
     A phone can only run one VPN at a time.
   - They only see that node: it's the Tailscale container, which serves nothing but
     the web.
   - To revoke access, remove the share.
2. **An account.** Registration is closed: `keycloak-setup` turns it off on every start.
   - In the admin console, open the `shodoukan` realm → Users → Add user, set a
     temporary password under Credentials, and send it to them.
   - Keycloak asks them for a new password at their first sign-in.
   - To remove someone, disable or delete the user.

## Operations

### Deploy and roll back

```bash
deploy/deploy.sh                      # deploy origin/main
deploy/deploy.sh 1a2b3c4              # deploy (or roll back to) a commit, branch or tag
deploy/deploy.sh saul205/52_deployment   # try a branch on pre before merging
deploy/deploy.sh ps                   # any compose command: logs -f keycloak, stop, exec ...
```

A deploy runs these steps:

1. Checks out the ref in a separate worktree (`~/.cache/shodoukan-deploy`). Your
   checkout is never touched, and pre only runs committed code.
2. Builds the images, tagged with the commit's short SHA.
3. Backs up both databases, if they're running.
4. Runs `up -d`. `practice-migrate` runs `alembic upgrade head` before `practice-api`
   starts, and `keycloak-setup` reapplies the Keycloak settings.
5. Waits until `/`, `/practice-api/health` and `/idp/realms/shodoukan` answer.

Migrations are append-only and never run backwards. Rolling back past a migration
leaves a newer schema under older code: restore the backup taken before the deploy
instead.

Old images pile up, one set per deployed commit. Clean them with
`docker image prune` (dangling) or `docker image rm shodoukan-pre/<image>:<sha>`.

### Monthly dictionary refresh

`shodoukan-db` publishes a new dictionary at the start of each month.

- **Pre:** every deploy asks GitHub for the latest release and passes it to the build
  (`DICT_RELEASE`). The dictionary has its own build stage, so a new release is
  downloaded on the next deploy, and code changes alone never download it again.
- **Render:** `scheduled.yml` redeploys the API on the 2nd of each month.

Imported library items are snapshots, so a refresh never changes users' data.

### Copying dev users into pre (`seed`)

```bash
deploy/deploy.sh seed kl4ws     # or set SEED_USERS in deploy/.env.pre
```

`seed` **replaces all of pre's practice data**. If pre has users, it asks you to type
`replace`, and it backs up first. It needs the dev stack running. It copies the dev
realm users you name, or all of them if you name none:

- **Their Keycloak accounts,** with ids and password hashes. It exports them with
  `kc.sh export`, because the admin API doesn't return password hashes, and adds them to
  pre's realm with a partial import. A pre user with the same username is overwritten.
- **Their practice data.** It copies the dev practice database over pre's and deletes
  every other user, whose rows cascade. Then it migrates the database.

Since `users.id` is the token's `sub`, the copied users sign in to pre with their dev
passwords and find their own data. Pre keeps its own realm settings and clients.

### Backups

`practice-db-backup` and `keycloak-db-backup` dump each database nightly into their own
volume (`practice-backups`, `keycloak-backups`), with 7 daily and 4 weekly dumps kept.
Each volume has `last/`, `daily/`, `weekly/` and `monthly/` folders, and
`last/<db>-latest.sql.gz` points at the newest dump. `deploy.sh` also takes one before
every deploy and seed.

```bash
deploy/deploy.sh backup
# Copy the dumps off the machine (e.g. to a synced Windows folder)
docker run --rm -v shodoukan-pre_practice-backups:/backups:ro \
  -v /mnt/c/Users/<you>/shodoukan-backups:/out alpine cp -rL /backups/. /out/practice/
# Restore the practice DB from the latest dump into an empty schema
set -a; . deploy/.env.pre; set +a
deploy/deploy.sh stop practice-api
deploy/deploy.sh exec -T practice-db psql -U "$PRACTICE_DB_USER" -d "$PRACTICE_DB_NAME" \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
deploy/deploy.sh exec -T practice-db-backup cat /backups/last/shodoukan_practice-latest.sql.gz \
  | gunzip | deploy/deploy.sh exec -T practice-db psql -q -U "$PRACTICE_DB_USER" -d "$PRACTICE_DB_NAME"
deploy/deploy.sh start practice-api
```

Keycloak's database restores the same way: use `keycloak-db-backup`, the `keycloak`
database and `KEYCLOAK_DB_USER`, with Keycloak stopped.

### Changing passwords

Postgres stores a user's password when its volume is created and then ignores
`POSTGRES_PASSWORD`. Editing `.env.pre` alone makes the API fail with "password
authentication failed". Change the password in the database first, then in the
`.env`, then redeploy. Inside the container, `psql` needs no password:

```bash
set -a; . deploy/.env.pre; set +a
deploy/deploy.sh exec practice-db psql -U "$PRACTICE_DB_USER" -d "$PRACTICE_DB_NAME" \
  -c "ALTER USER \"$PRACTICE_DB_USER\" PASSWORD '<new>'"
# edit deploy/.env.pre, then:
deploy/deploy.sh up -d
```

Keycloak's admin password works the same way: `KC_BOOTSTRAP_ADMIN_*` only applies on
the very first start. Change it in the admin console, then in `.env.pre`.

### Keycloak admin

The admin console and the master realm are never served on `PUBLIC_URL`: Caddy
answers 404 for them. They're only on `http://localhost:8181/idp/admin`, on this
machine. Sign in with `KEYCLOAK_ADMIN_USER` / `KEYCLOAK_ADMIN_PASSWORD`.

Keycloak can't take some settings at startup, so after every start the one-shot
`keycloak-setup` service runs `docker/keycloak/setup.sh` (idempotent):

- **Closes registration** in the `shodoukan` realm.
- **Points the clients' redirect URIs and web origins at `PUBLIC_URL`.** The realm file
  is only imported once, so a realm created under another URL would otherwise keep the
  old one.
- **Moves the master realm's sign-in to the admin URL.** `KC_HOSTNAME_ADMIN` only moves
  the console itself, and its login form would otherwise post to the public URL, where
  Caddy blocks it.

The script signs in with the admin credentials from `.env.pre`. If they stop matching
it only logs a warning, but those settings are no longer applied.

### Moving to another machine

1. On the old host, take a backup and copy the dumps off it, then run
   `deploy/deploy.sh down`.
2. Remove the old `shodoukan` node in the Tailscale admin console, so the new one gets
   the same name and URL. Shares are per node, so share it with your friends again.
3. On the new host:
   - Install Docker Engine.
   - Clone the repo and copy `deploy/.env.pre`, with a new `TS_AUTHKEY`.
   - Run `deploy/deploy.sh`, then restore the dumps.

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

The free instance sleeps after 15 minutes without traffic, and waking it takes 30–60 s.
`scheduled.yml` pings `$DICT_API_URL/health` every 10 minutes. One always-on service
uses about 744 of the 750 free instance hours a month, so **don't add a second free web
service**: the static site uses no instance hours. GitHub pauses scheduled workflows
after 60 days without repository activity. Re-enable it from the Actions tab, or use an
external pinger such as cron-job.org (free, no card).

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
| `scheduled.yml` | Every 10 min; the 2nd of each month | Pings the Render API; redeploys it monthly |

Secrets: `RENDER_HOOK_DICT_API`, `RENDER_HOOK_DICT_WEB`. Variable: `DICT_API_URL`.
Nothing from GitHub runs on the pre host: pre is deployed by hand with
`deploy/deploy.sh`.
