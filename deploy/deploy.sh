#!/usr/bin/env bash
# Pre: builds and runs the practice stack on this machine (deploy/compose.yml),
# shared through Tailscale. Docs: docs/technical/deployment.md.
#
#   deploy/deploy.sh [ref]           deploy a commit (default: origin/main; any
#                                    branch, tag or SHA also works, e.g. to roll
#                                    back): build it, back up, migrate, restart
#   deploy/deploy.sh backup          dump both databases now
#   deploy/deploy.sh seed [user ...] replace pre's data with dev users (default:
#                                    SEED_USERS in .env.pre, or all): their
#                                    accounts with passwords and their data
#   deploy/deploy.sh <compose args>  e.g. ps, logs -f keycloak, down, exec ...
#
# The code is built from a separate git worktree (SHODOUKAN_DEPLOY_WORKTREE,
# default ~/.cache/shodoukan-deploy), so the checkout you work in is never
# touched and pre only ever runs committed code.
set -euo pipefail

DEPLOY_DIR=$(cd "$(dirname "$0")" && pwd)
REPO=$(dirname "$DEPLOY_DIR")
ENV_FILE=$DEPLOY_DIR/.env.pre
WORKTREE=${SHODOUKAN_DEPLOY_WORKTREE:-$HOME/.cache/shodoukan-deploy}
read -r -a COMPOSE_CMD <<< "${COMPOSE_BIN:-docker compose}"

if [[ ! -f $ENV_FILE ]]; then
  echo "Missing deploy/.env.pre: copy deploy/.env.pre.example and fill it in." >&2
  exit 1
fi

compose() {
  if [[ ! -f $WORKTREE/deploy/compose.yml ]]; then
    echo "Nothing deployed yet: run deploy/deploy.sh first." >&2
    exit 1
  fi
  # Images are tagged with the deployed commit.
  TAG=$(git -C "$WORKTREE" rev-parse --short=7 HEAD) \
    "${COMPOSE_CMD[@]}" -f "$WORKTREE/deploy/compose.yml" --env-file "$ENV_FILE" "$@"
}

is_running() {
  [[ -n $(compose ps --status running --quiet "$1" 2>/dev/null) ]]
}

backup() {
  local service
  for service in practice-db-backup keycloak-db-backup; do
    if is_running "$service"; then
      compose exec -T "$service" /backup.sh >/dev/null
      echo "✓ backup: ${service%-backup}"
    fi
  done
}

# Waits until Caddy answers for the SPA, the practice API and Keycloak's
# realm, checking from inside the web container.
smoke_test() {
  local path deadline=$((SECONDS + 240))
  for path in / /practice-api/health /idp/realms/shodoukan; do
    until compose exec -T web wget -q -O /dev/null "http://127.0.0.1${path}" 2>/dev/null; do
      if ((SECONDS > deadline)); then
        echo "✗ ${path} is not answering; see: deploy/deploy.sh logs" >&2
        return 1
      fi
      sleep 5
    done
    echo "✓ ${path}"
  done
}

deploy() {
  local ref=${1:-origin/main}
  git -C "$REPO" fetch --quiet origin
  git -C "$REPO" worktree prune
  if [[ -d $WORKTREE ]]; then
    git -C "$WORKTREE" checkout --quiet --force --detach "$ref"
  else
    git -C "$REPO" worktree add --quiet --detach "$WORKTREE" "$ref"
  fi
  echo "Deploying $(git -C "$WORKTREE" log -1 --format='%h: %s')"

  # The latest dictionary release; a new one invalidates the cached download.
  DICT_RELEASE=$(curl -fsS https://api.github.com/repos/saul205/shodoukan-db/releases/latest \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])' 2>/dev/null) \
    || DICT_RELEASE=latest
  export DICT_RELEASE
  echo "Dictionary release: ${DICT_RELEASE}"

  compose build
  backup
  compose up -d --remove-orphans
  smoke_test
  echo "Deployed $(git -C "$WORKTREE" rev-parse --short=7 HEAD) on $(grep '^PUBLIC_URL=' "$ENV_FILE" | cut -d= -f2-)"
}

# Replaces pre's data with dev users, named as arguments, in SEED_USERS or,
# if neither, all of them:
#  - their Keycloak accounts (ids and password hashes) into pre's realm, with
#    a partial import, so they sign in with their dev passwords; the admin
#    API doesn't return password hashes, hence kc.sh export. Only users: pre
#    keeps its own realm settings and clients.
#  - the practice database, minus every other user (their rows cascade), then
#    migrated. users.id is the token's sub, so each user owns their data.
seed() {
  local dev_db_container=shodoukan-practice-db-1 dev_keycloak=shodoukan-keycloak-1
  set -a; source "$REPO/.env.dev"; set +a
  local dev_user=$POSTGRES_USER dev_db=$POSTGRES_DB
  set -a; source "$ENV_FILE"; set +a
  local wanted="${*:-${SEED_USERS:-}}"

  compose up -d practice-db keycloak --wait
  local existing
  existing=$(compose exec -T practice-db psql -U "$PRACTICE_DB_USER" -d "$PRACTICE_DB_NAME" \
    -tAc "SELECT string_agg(username, ', ') FROM users" 2>/dev/null || true)
  if [[ -n $existing ]]; then
    echo "This replaces every user's data in pre (now: ${existing})."
    read -r -p "Type 'replace' to continue: " answer
    [[ $answer == replace ]] || { echo "Cancelled."; return 1; }
    backup
  fi

  echo "Exporting users from the dev realm (${dev_keycloak})..."
  local import ids
  import=$(docker exec "$dev_keycloak" sh -c '
    f=/tmp/seed-users.json
    /opt/keycloak/bin/kc.sh export --realm shodoukan --users same_file --file "$f" \
      --http-management-port=9876 >/dev/null 2>&1 && cat "$f"; status=$?
    rm -f "$f"; exit $status' \
    | WANTED="$wanted" python3 -c 'import json, os, sys
wanted = os.environ["WANTED"].replace(",", " ").split()
users = [u for u in json.load(sys.stdin).get("users", [])
         if not u["username"].startswith("service-account-")
         and (not wanted or u["username"] in wanted)]
missing = set(wanted) - {u["username"] for u in users}
if missing:
    sys.exit("Not in the dev realm: " + ", ".join(sorted(missing)))
print(json.dumps({"ifResourceExists": "OVERWRITE", "users": users}))')
  ids=$(python3 -c 'import json, sys
print(",".join("\x27%s\x27" % u["id"] for u in json.load(sys.stdin)["users"]))' <<< "$import")
  if [[ -z $ids ]]; then
    echo "No users to copy." >&2
    return 1
  fi

  echo "Copying ${dev_db} from ${dev_db_container} into pre..."
  compose exec -T practice-db psql -q -U "$PRACTICE_DB_USER" -d "$PRACTICE_DB_NAME" \
    -c 'SET client_min_messages = warning; DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
  docker exec "$dev_db_container" pg_dump -U "$dev_user" -d "$dev_db" -Fc --no-owner --no-privileges \
    | compose exec -T practice-db pg_restore -U "$PRACTICE_DB_USER" -d "$PRACTICE_DB_NAME" --no-owner
  compose exec -T practice-db psql -q -U "$PRACTICE_DB_USER" -d "$PRACTICE_DB_NAME" \
    -c "DELETE FROM users WHERE id::text NOT IN (${ids})"
  compose run --rm practice-migrate

  echo "Importing the users into pre's realm..."
  compose exec -T keycloak sh -c '
    K=/opt/keycloak/bin/kcadm.sh; C=/tmp/kcadm-seed.config
    $K config credentials --config $C --server http://localhost:8080/idp --realm master \
      --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null &&
    $K create partialImport --config $C -r shodoukan -f - -o' <<< "$import" \
    | python3 -c 'import json, sys
r = json.load(sys.stdin)
names = ", ".join(x["resourceName"] for x in r.get("results", []))
print("Seeded %s: they sign in to pre with their dev passwords." % names)'
  compose up -d
}

case "${1:-}" in
  "" | origin/* ) deploy "$@" ;;
  backup) backup ;;
  seed) shift; seed "$@" ;;
  -h | --help) sed -n '2,16p' "$DEPLOY_DIR/deploy.sh" | sed 's/^# \{0,1\}//' ;;
  *)
    # A git ref deploys it; anything else goes to compose.
    if git -C "$REPO" rev-parse --verify --quiet "${1}^{commit}" >/dev/null; then
      deploy "$1"
    else
      compose "$@"
    fi
    ;;
esac
