# Production Keycloak (pre and prod): an optimized build for PostgreSQL,
# served under /idp behind Caddy, with the deployed realm baked in.
# Build from the repo root:
#   docker build -f docker/keycloak/Dockerfile .
# Local development keeps using the stock image in start-dev mode
# (docker-compose.yml).

FROM quay.io/keycloak/keycloak:26.3 AS builder

# Build-time options. The management interface (port 9000, health checks)
# stays at the root so the healthcheck doesn't depend on the public path.
ENV KC_DB=postgres \
    KC_HEALTH_ENABLED=true \
    KC_HTTP_RELATIVE_PATH=/idp \
    KC_HTTP_MANAGEMENT_RELATIVE_PATH=/
RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:26.3

COPY --from=builder /opt/keycloak/ /opt/keycloak/
# Imported on first start only (when the realm doesn't exist yet). Its
# ${PUBLIC_URL} placeholders are filled from the environment.
COPY docker/keycloak/prod/realm-shodoukan.json /opt/keycloak/data/import/

ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
CMD ["start", "--optimized", "--import-realm"]
