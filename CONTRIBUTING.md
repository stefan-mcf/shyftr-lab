# Contributing to ShyftR

ShyftR is currently a controlled-pilot, local-first MVP. Contributions should preserve append-only Cell truth, review gates, and public-surface hygiene.

## Local setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev,service]'
python -m pytest -q
bash examples/run-local-lifecycle.sh
python scripts/public_readiness_check.py
```

For console changes:

```bash
cd apps/console
npm install
npm run build
npm audit --omit=dev
```

## Pull request expectations

- Keep examples synthetic and free of secrets/private data.
- Add or update tests for behavior changes.
- Update docs when CLI/API/console behavior changes.
- Do not expand distributed multi-cell intelligence without a prior issue/plan.
- Preserve local-first behavior; no hidden cloud or external-service dependency in default tests.
