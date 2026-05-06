#!/usr/bin/env bash
set -euo pipefail

out_dir="${TMPDIR:-/tmp}/shyftr-alpha-report"
mkdir -p "$out_dir"
env_file="$out_dir/environment.json"
gate_log="$out_dir/alpha_gate.log"

python_bin="${PYTHON:-python3}"
sha="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
cat > "$env_file" <<JSON
{
  "git_sha": "$sha",
  "os": "$(uname -s 2>/dev/null || echo unknown)",
  "os_version": "$(uname -r 2>/dev/null || echo unknown)",
  "arch": "$(uname -m 2>/dev/null || echo unknown)",
  "python": "$($python_bin --version 2>&1 || echo missing)",
  "node": "$(node --version 2>/dev/null || echo missing)",
  "npm": "$(npm --version 2>/dev/null || echo missing)"
}
JSON

set +e
bash scripts/release_gate.sh 2>&1 | tee "$gate_log"
code=${PIPESTATUS[0]}
set -e

echo
echo "Environment capture: $env_file"
echo "Release gate log: $gate_log"
echo "Exit code: $code"
echo
echo "Open a report with: https://github.com/stefan-mcf/shyftr/issues/new?template=alpha_test_report.yml"
exit "$code"
