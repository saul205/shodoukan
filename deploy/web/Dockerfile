# The practice stack's entry point: Caddy serving the practice SPA (static
# files) and proxying /practice-api and /idp. Build from the repo root:
#   docker build -f deploy/web/Dockerfile .

# ── build stage ───────────────────────────────────────────────────────────────
FROM node:22-alpine AS build

RUN corepack enable
WORKDIR /repo

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/shodoukan-ui ./packages/shodoukan-ui
COPY packages/shodoukan-practice-web ./packages/shodoukan-practice-web
RUN pnpm install --frozen-lockfile --filter "shodoukan-practice-web..."

# Same-host paths, so one build works on any host (pre and prod).
ENV NUXT_PUBLIC_API_BASE=/practice-api \
    NUXT_PUBLIC_AUTH_ISSUER=/idp/realms/shodoukan
RUN pnpm --filter shodoukan-ui build \
 && pnpm --filter shodoukan-practice-web generate

# ── runtime stage ─────────────────────────────────────────────────────────────
FROM caddy:2-alpine

COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /repo/packages/shodoukan-practice-web/.output/public /srv
