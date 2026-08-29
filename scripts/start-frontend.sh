#!/usr/bin/env bash
# Runs the Next.js dev server in the foreground on port 3000.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root/frontend"

if [ ! -f .env.local ]; then
  cp .env.example .env.local
fi

npm run dev -- --port 3000
