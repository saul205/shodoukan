#!/usr/bin/env bash
# Pre: the production stack on this machine, built from the working tree,
# on http://localhost:8088 (WEB_PORT). Its databases are its own.
#
#   deploy/pre.sh up      build and start (data is kept between runs)
#   deploy/pre.sh down    stop; nothing runs, data is kept
#   deploy/pre.sh reset   stop and delete pre's data (next up starts clean:
#                         migrations from zero, realm imported again)
#   deploy/pre.sh seed    copy dev into pre: the practice database (then
#                         migrated, to test new migrations on existing data)
#                         and the dev realm's users with their passwords
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

seed() {
  # The dev database (repo docker-compose.yml) and its credentials.
  local dev_container=shodoukan-practice-db-1
  set -a; source ../.env.dev; set +a
  local dev_user=$POSTGRES_USER dev_db=$POSTGRES_DB
  set -a; source .env.pre; set +a

  compose up -d practice-db --wait
  echo "Copying ${dev_db} from ${dev_container} into pre..."
  compose exec -T practice-db psql -q -U "$PRACTICE_DB_USER" -d "$PRACTICE_DB_NAME" \
    -c 'SET client_min_messages = warning; DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
  docker exec "$dev_container" pg_dump -U "$dev_user" -d "$dev_db" -Fc --no-owner --no-privileges \
    | compose exec -T practice-db pg_restore -U "$PRACTICE_DB_USER" -d "$PRACTICE_DB_NAME" --no-owner
  compose run --rm practice-migrate
  seed_users
  echo "Seeded. Dev users sign in to pre with their dev passwords."
}

# Copies the dev realm's users (ids and password hashes) into pre's realm, so
# they can sign in and own the practice data copied above (users.id is the
# token's sub). Only users: pre keeps its own realm settings and clients.
# The admin API doesn't return password hashes, hence kc.sh export.
seed_users() {
  local dev_keycloak=shodoukan-keycloak-1
  compose up -d keycloak --wait
  echo "Copying the dev realm's users from ${dev_keycloak} into pre..."
  docker exec "$dev_keycloak" sh -c '
    f=/tmp/seed-users.json
    /opt/keycloak/bin/kc.sh export --realm shodoukan --users same_file --file "$f" \
      --http-management-port=9876 >/dev/null 2>&1 && cat "$f"; status=$?
    rm -f "$f"; exit $status' \
    | python3 -c 'import json, sys
realm = json.load(sys.stdin)
users = [u for u in realm.get("users", []) if not u["username"].startswith("service-account-")]
print(json.dumps({"ifResourceExists": "OVERWRITE", "users": users}))' \
    | compose exec -T keycloak sh -c '
      K=/opt/keycloak/bin/kcadm.sh; C=/tmp/kcadm-seed.config
      $K config credentials --config $C --server http://localhost:8080/idp --realm master \
        --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null &&
      $K create partialImport --config $C -r shodoukan -f - -o' \
    | python3 -c 'import json, sys
r = json.load(sys.stdin)
print("Users: %s added, %s overwritten" % (r["added"], r["overwritten"]))'
}

case "${1:-}" in
  up)
    compose up -d --build --remove-orphans
    smoke_test
    echo "Pre is up on $(grep '^PUBLIC_URL=' .env.pre | cut -d= -f2-)"
    ;;
  down) compose down ;;
  reset) compose down --volumes ;;
  seed) seed ;;
  "") sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
  *) compose "$@" ;;
esac
