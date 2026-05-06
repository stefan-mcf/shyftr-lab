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

echo "== ShyftR release gate =="
echo "Status: stable local-first release"
echo "Data policy: synthetic or operator-approved data only; do not use sensitive production memory for this gate."
echo

echo "== Python and CLI smoke =="
"$PYTHON_BIN" --version
"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(f"ShyftR release gate requires Python 3.11+; got {sys.version.split()[0]}")
PY
"$PYTHON_BIN" -m shyftr.cli --help >/dev/null

echo "== Public release/readiness posture =="
"$PYTHON_BIN" scripts/public_readiness_check.py

echo "== Python test suite =="
"$PYTHON_BIN" -m pytest -q

echo "== Deterministic local lifecycle =="
PYTHON="$PYTHON_BIN" bash examples/run-local-lifecycle.sh

echo "== Synthetic replacement-readiness replay =="
"$PYTHON_BIN" - <<'PY'
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from shyftr.layout import init_cell
from shyftr.readiness import replacement_pilot_readiness

with TemporaryDirectory(prefix="shyftr-release-gate-") as tmp:
    cell = init_cell(Path(tmp) / "release-gate-cell", "release-gate-cell", cell_type="user")
    report = replacement_pilot_readiness(cell, run_replay=True)
    print(f"readiness_status={report.status}")
    print(f"readiness_ready={report.ready}")
    if report.blockers:
        print("readiness_blockers=" + ", ".join(report.blockers))
        raise SystemExit(1)
    replay = report.replay_report or {}
    print(f"replay_status={replay.get('status')}")
    print(f"diagnostic_count={report.diagnostic_summary.get('diagnostic_count', 0)}")
PY

if [ -d apps/console ] && command -v npm >/dev/null 2>&1; then
  echo "== Console build and production-dependency audit =="
  (cd apps/console && npm ci && npm run build && npm audit --omit=dev)
else
  echo "== Console check skipped: npm unavailable =="
fi

echo
echo "SHYFTR_RELEASE_READY"
