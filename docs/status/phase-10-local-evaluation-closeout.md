# Phase 10 local evaluation closeout

Status: implemented locally in the working tree; not yet committed in this artifact.

Recorded: 2026-05-06T15:22:32Z

Pre-implementation SHA: `528dd14649f8b4cac69579c349c5fa891d1c45da`

## Scope completed

Phase 10 only:

- deterministic local memory effectiveness metrics from retrieval logs and feedback ledgers;
- transparent decay scoring that informs retrieval scoring without direct memory mutation;
- review-gated decay/deprecation reporting remains proposal-only;
- reproducible local demo artifacts for closeout-to-memory-to-pack evaluation;
- CLI surfaces for `shyftr metrics` and `shyftr decay`;
- console/API metrics now include Phase 10 metric summaries while preserving existing pilot metric fields.

Not started:

- Phase 11 CI/release/operating-discipline work;
- Checkpoint E alpha-exit;
- Checkpoint F stable-release wording;
- hosted-service, production, package-release, or private-core-heavy claims.

## Research adaptation

Before implementation, a dedicated research pass compared the original Phase 10 plan against current memory/RAG evaluation patterns and the live ShyftR codebase. The implementation adapted the plan as follows:

- use deterministic retrieval precision/recall-style proxies rather than LLM-as-judge metrics;
- reuse existing append-only retrieval and feedback ledgers instead of creating a second metrics truth store;
- add public-safe transparent decay factors: age, failed reuse, low confidence, and supersession;
- wire decay into the existing hybrid retrieval `decay` component rather than introducing a parallel ranking path;
- keep deprecation review-gated and proposal-only;
- after independent review, accept both top-level and metadata feedback id fields and de-duplicate them per feedback row so older feedback ledgers remain counted without double-counting.

## Files changed

- `src/shyftr/metrics.py`
- `src/shyftr/decay.py`
- retrieval assembly module
- `src/shyftr/cli.py`
- `src/shyftr/console_api.py`
- `tests/test_metrics.py`
- `tests/test_decay.py`
- `tests/test_demo_flow.py`
- `examples/closeout.md`
- `examples/packet.json`
- `docs/demo.md`
- `docs/status/phase-10-local-evaluation-closeout.md`

## Verification

Passed locally:

```text
PYTHONPATH=src python3 -m pytest -q tests/test_metrics.py tests/test_decay.py tests/test_demo_flow.py
19 passed

python3 scripts/terminology_inventory.py --fail-on-public-stale
PASS

python3 scripts/terminology_inventory.py --fail-on-capitalized-prose
PASS

python3 scripts/public_readiness_check.py
ShyftR public readiness check
PASS

git diff --check
PASS

PYTHONPATH=src python3 -m pytest -q
890 passed, 27 warnings

bash scripts/alpha_gate.sh
ALPHA_GATE_READY
```

## Closeout scope boundary

This artifact records local implementation evidence. It does not claim final commit SHA, pushed CI, alpha-exit, stable release, hosted service readiness, production readiness, or package-release readiness.
