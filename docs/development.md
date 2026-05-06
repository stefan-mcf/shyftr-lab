# ShyftR Development

## Prerequisites

- Python 3.11 or newer.
- Node.js 20 or compatible npm for the optional console.
- No network services or API keys are required for tests, examples, or public-readiness checks after dependencies are installed.

## Python setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev,service]'
shyftr --help
python -m pytest -q
```

The `service` extra is needed for FastAPI/uvicorn service tests such as `tests/test_server.py` and `tests/test_console_api.py`.

## Console setup

```bash
cd apps/console
npm install
npm run build
npm audit --omit=dev
```

## Main local gates

```bash
bash examples/run-local-lifecycle.sh
python scripts/public_readiness_check.py
bash scripts/check.sh
bash scripts/smoke-install.sh
bash scripts/release_gate.sh
```

Use `scripts/release_gate.sh` before operator release-scope review. It uses synthetic data only and should end with `SHYFTR_RELEASE_READY`. See `docs/status/release-readiness.md` for scope and data boundaries.

## Optional dependency notes

The `lancedb` extra is optional. The default public smoke path uses deterministic local embeddings and does not require LanceDB.

## Troubleshooting

- If `shyftr` is not found, activate the venv or run with `PYTHONPATH=src python -m shyftr.cli --help`.
- If FastAPI imports fail, install `.[service]`.
- If console audit reports dependency vulnerabilities, record the exact npm output in `docs/status/public-readiness-audit.md` before deciding whether the issue blocks publication.
