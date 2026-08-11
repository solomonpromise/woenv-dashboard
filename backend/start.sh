#!/bin/sh
# Container entrypoint. Render and docker-compose both run this rather than
# uvicorn directly, so the schema is current before the API accepts traffic.
set -e

# Idempotent: creates any missing tables, adds any missing columns, and exits 0
# against a database that is already up to date.
python -m scripts.migrate_schema

# Render's free plan has no shell, so this is how the first admin gets created.
# Set ADMIN_PASSWORD (and optionally ADMIN_USERNAME / ADMIN_EMAIL) for the first
# deploy, then remove it - seed_admin is a no-op once the user exists.
if [ -n "$ADMIN_PASSWORD" ]; then
    python -m scripts.seed_admin
fi

# Render injects $PORT and expects the process to bind it. Compose does not, so
# fall back to the port the image documents.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
