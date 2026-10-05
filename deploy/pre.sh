#!/usr/bin/env bash
# Pre: the production stack on this machine, built from the working tree,
# on http://localhost:8088 (WEB_PORT). Its databases are its own.
#
#   deploy/pre.sh up      build and start (data is kept between runs)
#   deploy/pre.sh down    stop; nothing runs, data is kept
#   deploy/pre.sh reset   stop and delete pre's data (next up starts clean:
#                         migrations from zero, realm imported again)
#   deploy/pre.sh seed [user ...]
#                         copy dev users (default: SEED_USERS in .env.pre, or
#                         all) into pre: their Keycloak accounts with their
#                         passwords and their practice data, then migrate
#   deploy/pre.sh logs [service] | ps | <any compose command>
set -euo pipefail

cd "$(dirname "$0")"
source ./lib.sh

if [[ ! -f .env.pre ]]; then
  echo "Missing deploy/.env.pre: copy deploy/.env.pre.example and fill it in." >&2
  exit 1
fi

compose() {
  "${COMPOSE_CMD[@]}" -f compose.yml -f compose.pre.yml --env-file .env.pre "$@"
}

# Copies dev into pre, for the dev realm users named as arguments, in
# SEED_USERS (deploy/.env.pre) or, if neither, all of them:
#  - their Keycloak accounts (ids and password hashes) into pre's realm, with
#    a partial import, so they sign in to pre with their dev passwords; the
#    admin API doesn't return password hashes, hence kc.sh export. Only users:
#    pre keeps the prod realm's settings and clients.
#  - the practice database, minus every other user (their rows cascade), then
#    migrated, to test new migrations on existing data. users.id is the
#    token's sub, so each user owns their copied data.
seed() {
  local dev_db_container=shodoukan-practice-db-1 dev_keycloak=shodoukan-keycloak-1
  set -a; source ../.env.dev; set +a
  local dev_user=$POSTGRES_USER dev_db=$POSTGRES_DB
  set -a; source .env.pre; set +a
  local wanted="${*:-${SEED_USERS:-}}"

  echo "Exporting users from the dev realm (${dev_keycloak})..."
  local import
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
  local ids
  ids=$(python3 -c 'import json, sys
print(",".join("\x27%s\x27" % u["id"] for u in json.load(sys.stdin)["users"]))' <<< "$import")
  if [[ -z "$ids" ]]; then
    echo "No users to copy." >&2
    return 1
  fi

  compose up -d practice-db keycloak --wait
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
}

case "${1:-}" in
  up)
    compose up -d --build --remove-orphans
    smoke_test
    echo "Pre is up on $(grep '^PUBLIC_URL=' .env.pre | cut -d= -f2-)"
    ;;
  down) compose down ;;
  reset) compose down --volumes ;;
  seed) shift; seed "$@" ;;
  "") sed -n '2,12p' "$(basename "$0")" | sed 's/^# \{0,1\}//'; exit 1 ;;
  *) compose "$@" ;;
esac
