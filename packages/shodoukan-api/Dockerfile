# ── dictionary ────────────────────────────────────────────────────────────────
# The latest shodoukan-db release, straight from its download URL (no GitHub
# API call, so no rate limit). For a remote ADD, BuildKit checks the file on
# every build and only reuses the cached layer while it's unchanged, so the
# monthly redeploy picks up a new release even with Render's build cache.
FROM alpine:3 AS dictionary

ADD https://github.com/saul205/shodoukan-db/releases/latest/download/shodoukan.sqlite /shodoukan.sqlite
# Remote ADDs are created 0600; the API runs as a non-root user.
RUN chmod 644 /shodoukan.sqlite

# ── build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install pinned deps first — this layer is cached unless requirements.txt changes.
COPY packages/shodoukan-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the local packages without re-resolving deps.
COPY packages/shodoukan ./packages/shodoukan
COPY packages/shodoukan-api ./packages/shodoukan-api
RUN pip install --no-cache-dir --no-deps \
    ./packages/shodoukan \
    ./packages/shodoukan-api

# ── runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN useradd --system --no-create-home appuser && mkdir /data

# Before the code, so a code change doesn't add another 350 MB layer.
COPY --from=dictionary /shodoukan.sqlite /data/shodoukan.sqlite
COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

ENV SHODOUKAN_DB_PATH=/data/shodoukan.sqlite

USER appuser
EXPOSE 8000

CMD ["uvicorn", "shodoukan_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
