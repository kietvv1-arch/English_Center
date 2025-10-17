#!/usr/bin/env bash

set -e

: "${POSTGRES_HOST:=db}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_USER:=postgres}"

# Wait for Postgres to become available before starting the app.
if command -v pg_isready >/dev/null 2>&1; then
  until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
    >&2 echo "Postgres is unavailable - sleeping"
    sleep 1
  done
fi

>&2 echo "Postgres is up - continuing"

exec "$@"
