#!/usr/bin/env bash
# Pre: the production stack on this machine, built from the working tree,
# on http://localhost:8088 (WEB_PORT). Its databases are its own.
#
#   deploy/pre.sh up      build and start (data is kept between runs)
#   deploy/pre.sh down    stop; nothing runs, data is kept
#   deploy/pre.sh reset   stop and delete pre's data (next up starts clean:
#                         migrations from zero, realm imported again)
#   deploy/pre.sh seed    copy the dev practice database into pre and migrate
#                         it, to test new migrations on existing data
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
  echo "Seeded. Its users belong to the dev realm, so sign in to pre with a new user."
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
