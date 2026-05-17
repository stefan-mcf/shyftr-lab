# ShyftR Phase 11 P11-2 Closeout: mem0 OSS Compatibility

Date: 2026-05-17
Repo: `/Users/stefan/ShyftR`
Baseline HEAD: `c68a1061c485f515af193babb2394c59c0ce2f10`
Status: P11-2 implemented locally; verification recorded below

## Verdict

P11-2 adds an optional mem0 OSS/local comparator path to the Phase 11 benchmark harness without making mem0 a required dependency and without adding mem0 Cloud or credential-backed behavior.

This is still a fixture-safe adapter-contract slice. It does not support broad ShyftR-vs-mem0 performance claims.

## Implemented surface

Code:

- `src/shyftr/benchmarks/adapters/base.py`
- `src/shyftr/benchmarks/adapters/__init__.py`
- `src/shyftr/benchmarks/adapters/mem0_backend.py`
- `src/shyftr/benchmarks/runner.py`
- `scripts/run_memory_benchmark.py`
- `tests/test_benchmark_adapter_contract.py`

Docs:

- `docs/benchmarks/README.md`

## What works

The harness now supports:

- explicit `--include-mem0-oss` CLI opt-in;
- default-off mem0 path so P11-1 ShyftR plus no-memory behavior remains the default;
- optional mem0 dependency detection;
- report status `skipped` when mem0 OSS is not installed;
- no mem0 Cloud/API-key path in the default public harness;
- best-effort mem0 OSS ingest/search normalization when a local mem0 package is available;
- stable fixture message identifiers where mem0 results expose `metadata.message_id`.

## Smoke command

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --run-id p11-2-controller-smoke \
  --output artifacts/benchmarks/p11_2_controller_report.json \
  --top-k 5 \
  --include-retrieval-details \
  --include-mem0-oss
```

Observed smoke result on this machine:

```text
schema_version: shyftr-memory-benchmark-report/v0
backends: [('shyftr', 'ok'), ('no-memory', 'ok'), ('mem0-oss', 'skipped')]
mem0 status_reason: mem0 (OSS) Python package not installed. Install an OSS/local mem0 package to enable this backend. This harness does not auto-install optional deps.
```

The generated smoke report was removed from the worktree after verification so the commit set remains code/docs/tests only.

## Verification performed

Focused verification:

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_adapter_contract.py
```

Result:

```text
3 passed
```

Full gate verification:

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_adapter_contract.py
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
PYTHONPATH=.:src pytest -q
```

Result:

```text
3 passed
ShyftR public readiness check
PASS
1098 passed, 40 warnings in 18.50s
```

Warnings are existing `httpx` TestClient deprecation warnings in FastAPI tests.

## Swarm execution

- `swarm2` first inspected P11-2 and correctly identified that `runner.py` needed to be in scope to represent `skipped` status.
- Scope was expanded to include `src/shyftr/benchmarks/runner.py`.
- `swarm2` then implemented the mem0 OSS adapter, skipped-status runner support, CLI flag, docs, and focused test.
- Controller verified files from disk, made the missing-dependency test deterministic across machines with or without mem0 installed, ran focused tests, and ran the smoke CLI.

## Deferred work

Next tranche should be P11-3: public-safe LOCOMO-mini or equivalent public dataset adapter/run.

Before P11-3, optionally tighten P11-2 with a version-pinned mem0 OSS integration test in an environment where mem0 is installed locally. That should stay conditional and must not require Cloud credentials.

## Claim rule

The current harness supports only this claim:

- ShyftR has a fixture-safe benchmark harness that can include ShyftR, no-memory, and optional mem0 OSS/local backends, and reports missing mem0 OSS as `skipped` instead of failing the run.

It does not support:

- broad ShyftR-vs-mem0 performance claims;
- LOCOMO, LongMemEval, or BEAM claims;
- mem0 Cloud claims;
- hosted or production claims;
- measured task-success lift.
