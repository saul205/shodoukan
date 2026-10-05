#!/usr/bin/env bash
# Prod: pulls the practice images published by CI and (re)starts the stack
# behind Tailscale Funnel. Run it on the host, from the repo checkout.
#
#   deploy/deploy.sh          deploy the latest images (main)
#   deploy/deploy.sh <sha>    deploy (or roll back to) the images of a commit
#   deploy/deploy.sh logs [service] | ps | <any compose command>
#
# Migrations run on every start (practice-migrate) and are append-only, so
# rolling back to an image older than the last migration isn't supported:
# restore a backup instead (docs/technical/deployment.md).
set -euo pipefail

cd "$(dirname "$0")"
source ./lib.sh

if [[ ! -f .env.prod ]]; then
  echo "Missing deploy/.env.prod: copy deploy/.env.prod.example and fill it in." >&2
  exit 1
fi

compose() {
  "${COMPOSE_CMD[@]}" -f compose.yml -f compose.prod.yml --env-file .env.prod "$@"
}

# No argument, "latest" or a commit SHA: deploy. Anything else: compose.
if [[ $# -eq 0 || "$1" == latest || "$1" =~ ^[0-9a-f]{7,40}$ ]]; then
  export TAG="${1:-latest}"
  echo "Deploying images tagged ${TAG}..."
  compose pull
  compose up -d --remove-orphans
  smoke_test
  echo "Deployed ${TAG} on $(grep '^PUBLIC_URL=' .env.prod | cut -d= -f2-)"
else
  compose "$@"
fi
