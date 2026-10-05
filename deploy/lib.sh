# Shared by pre.sh and deploy.sh (sourced, not run).

# `docker compose`; override with COMPOSE_BIN if the plugin lives elsewhere.
read -r -a COMPOSE_CMD <<< "${COMPOSE_BIN:-docker compose}"

# Waits until Caddy answers for the SPA, the practice API and Keycloak's
# realm, checking from inside the web container (no port needed on the host).
smoke_test() {
  local paths=(/ /practice-api/health /idp/realms/shodoukan)
  local deadline=$((SECONDS + 240))
  for path in "${paths[@]}"; do
    until compose exec -T web wget -q -O /dev/null "http://127.0.0.1${path}"; do
      if ((SECONDS > deadline)); then
        echo "✗ ${path} is not answering; see: ${0} logs" >&2
        return 1
      fi
      sleep 5
    done
    echo "✓ ${path}"
  done
}
