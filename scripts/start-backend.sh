#!/usr/bin/env bash
# Waits for Postgres to be ready, then runs the FastAPI dev server in the
# foreground with autoreload. Run scripts/start-docker.sh first (or in
# parallel — this script waits for it).
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"

echo "Waiting for Postgres..."
until (cd "$repo_root" && docker compose exec -T postgres pg_isready -U geoattend -d geoattend) >/dev/null 2>&1; do
  sleep 1
done
echo "Postgres is ready."

cd "$repo_root/backend"

if [ ! -f .env ]; then
  cp .env.example .env
fi

uv run uvicorn app.main:app --port 8001 --reload
