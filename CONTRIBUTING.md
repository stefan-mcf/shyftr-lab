# Contributing to ShyftR

ShyftR is currently a controlled-pilot, local-first MVP. Contributions should preserve append-only cell truth, review gates, and public-surface hygiene.

## local setup

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

## pull request expectations

- Keep examples synthetic and free of secrets or private data.
- Add or update tests for behavior changes, including regulator and policy changes covered by `docs/review-policy.md`.
- Update docs, migration notes, and `CHANGELOG.md` when CLI, API, console behavior, schema, or ledger format changes.
- Preserve provenance on every memory write path. Do not strip, rewrite, or fabricate provenance fields.
- Preserve local-first behavior; default tests must not require hidden cloud or external-service dependencies.
- Keep public claims tied to implemented and verified behavior.
- Preserve current ShyftR vocabulary in public docs and user-facing surfaces.

## schema migration notes

When a pull request changes SQLite schema, ledger format, JSONL event fields, or migration helpers, include:

- before and after shape;
- the migration step added, if any;
- whether existing local cells open without data loss or manual migration;
- compatibility behavior for older ledgers when relevant.

## review policy

All contributions must follow `docs/review-policy.md`. Memory safety, provenance preservation, local-first defaults, terminology hygiene, and review gates are required for merge readiness.
