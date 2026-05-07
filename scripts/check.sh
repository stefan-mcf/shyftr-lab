#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -n "${PYTHON:-}" ]; then
  PYTHON_BIN="$PYTHON"
elif [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.11)"
else
  PYTHON_BIN="python"
fi

export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

"$PYTHON_BIN" -m compileall -q src scripts examples
"$PYTHON_BIN" -m shyftr.cli --help >/dev/null
PYTHON="$PYTHON_BIN" bash examples/run-local-lifecycle.sh
if [ -d apps/console ] && command -v npm >/dev/null 2>&1; then
  (cd apps/console && npm run build && npm audit --omit=dev)
else
  echo "Skipping console check: npm not available"
fi
"$PYTHON_BIN" scripts/public_readiness_check.py
"$PYTHON_BIN" scripts/terminology_inventory.py --fail-on-public-stale
"$PYTHON_BIN" scripts/terminology_inventory.py --fail-on-capitalized-prose
