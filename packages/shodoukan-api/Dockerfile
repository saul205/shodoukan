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

RUN useradd --system --no-create-home appuser

COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

ENV SHODOUKAN_DB_PATH=/data/shodoukan.sqlite

USER appuser
EXPOSE 8000

CMD ["uvicorn", "shodoukan_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
