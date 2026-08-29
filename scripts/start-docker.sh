#!/usr/bin/env bash
# Starts Postgres (pgvector image) in the foreground so its logs stream into
# whichever terminal runs this script. Ctrl+C stops it.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

docker compose up postgres
