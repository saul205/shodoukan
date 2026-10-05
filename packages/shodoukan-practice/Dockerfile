# Practice API image. Build from the repo root:
#   docker build -f packages/shodoukan-practice/Dockerfile .
# The same image runs the API and, with
#   alembic -c packages/shodoukan-practice/alembic.ini upgrade head
# the migrations (deploy/compose.yml's practice-migrate service).

# ── build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY packages/shodoukan ./packages/shodoukan
COPY packages/shodoukan-practice ./packages/shodoukan-practice
RUN pip install --no-cache-dir ./packages/shodoukan ./packages/shodoukan-practice

# Download the dictionary and bake it into the image (read in-process by the
# dictionary gateway). The optional token avoids GitHub's anonymous rate limit.
RUN --mount=type=secret,id=github_token \
    GITHUB_TOKEN="$(cat /run/secrets/github_token 2>/dev/null || true)" \
    shodoukan-setup

# ── runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN useradd --system --no-create-home appuser && mkdir /data

COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/alembic /usr/local/bin/
COPY --from=builder /root/.local/share/shodoukan/shodoukan.sqlite \
                    /data/shodoukan.sqlite

# alembic.ini points its script_location at the package's source tree.
WORKDIR /app
COPY packages/shodoukan-practice/alembic.ini packages/shodoukan-practice/
COPY packages/shodoukan-practice/src/shodoukan_practice/infrastructure/db/migrations \
     packages/shodoukan-practice/src/shodoukan_practice/infrastructure/db/migrations

ENV SHODOUKAN_DB_PATH=/data/shodoukan.sqlite \
    PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8001

# Behind Caddy at /practice-api: UVICORN_ROOT_PATH=/practice-api (read by
# uvicorn) keeps the OpenAPI and Swagger URLs right.
CMD ["uvicorn", "shodoukan_practice.api.app:app", "--host", "0.0.0.0", \
     "--port", "8001", "--proxy-headers", "--forwarded-allow-ips", "*"]
