#!/usr/bin/env bash
# Starts Postgres (pgvector image) and Redis (Phase 7 rate limiting) in the
# foreground so their logs stream into whichever terminal runs this script.
# Ctrl+C stops both.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

docker compose up postgres redis
