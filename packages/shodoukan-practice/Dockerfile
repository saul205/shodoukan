# Practice API image. Build from the repo root:
#   docker build -f packages/shodoukan-practice/Dockerfile .
# The same image runs the API and, with
#   alembic -c packages/shodoukan-practice/alembic.ini upgrade head
# the migrations (deploy/compose.yml's practice-migrate service).

# ── dictionary ────────────────────────────────────────────────────────────────
# The dictionary SQLite, read in-process by the dictionary gateway. Its own
# stage, so code changes don't download it again: the layer is cached per
# DICT_RELEASE (a shodoukan-db release tag; deploy/deploy.sh passes the
# latest one, so a new release is picked up on the next deploy).
FROM alpine:3 AS dictionary

ARG DICT_RELEASE=latest
RUN if [ "$DICT_RELEASE" = latest ]; then \
      url=https://github.com/saul205/shodoukan-db/releases/latest/download/shodoukan.sqlite; \
    else \
      url="https://github.com/saul205/shodoukan-db/releases/download/$DICT_RELEASE/shodoukan.sqlite"; \
    fi \
 && wget -q -O /shodoukan.sqlite "$url"

# ── build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY packages/shodoukan ./packages/shodoukan
COPY packages/shodoukan-practice ./packages/shodoukan-practice
RUN pip install --no-cache-dir ./packages/shodoukan ./packages/shodoukan-practice

# ── runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN useradd --system --no-create-home appuser && mkdir /data

# Before the code, so a code change doesn't add another 350 MB layer.
COPY --from=dictionary /shodoukan.sqlite /data/shodoukan.sqlite
COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/alembic /usr/local/bin/

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
