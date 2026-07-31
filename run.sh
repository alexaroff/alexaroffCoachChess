#!/usr/bin/env bash
# alexaroffCoachChess launcher
# Double-click or run from terminal. Creates venv on first run if needed.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "→ alexaroffCoachChess"
echo "  dir: $ROOT"

# Optional update (non-fatal if offline / no changes)
if [ -d .git ]; then
  echo "→ git pull origin main"
  git pull origin main || echo "  (git pull skipped or failed — continuing with local)"
fi

# venv
if [ ! -d venv ]; then
  echo "→ creating venv + installing deps"
  python3 -m venv venv
  # shellcheck disable=SC1091
  source venv/bin/activate
  pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

echo "→ starting main.py"
exec python main.py
