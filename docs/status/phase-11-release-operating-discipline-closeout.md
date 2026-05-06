# Phase 11 release and operating discipline closeout

Status: implemented locally in the working tree; final commit, push, tag, and exact-SHA CI verification are recorded outside this artifact after landing.

Recorded: 2026-05-06T22:40:38Z

Preflight SHA before Phase 10/11 working-tree changes: `528dd14649f8b4cac69579c349c5fa891d1c45da`

## Scope completed

Phase 11 only:

- GitHub Actions CI was hardened for Python 3.11 and 3.12 tests, dependency caching, public quality gates, local lifecycle smoke, console build/audit, concurrency, least-privilege permissions, and job timeouts;
- contribution guidance now requires regulator/policy tests, migration notes, provenance-preserving memory write behavior, local-first defaults, and terminology hygiene;
- `docs/review-policy.md` records memory safety, schema, provenance, and review-gate requirements;
- the pull request template now includes policy, schema, provenance, public-claim, and cell-ledger truth checks;
- README governance links and changelog entries now point to the new review surface;
- status docs record the bounded Phase 11 scope and still-blocked release scopes;
- `v0.0.0-planning` is reserved for the final landed Phase 11 planning baseline commit.

Not started:

- Phase 12 or any further phase work;
- Checkpoint E alpha-exit;
- Checkpoint F stable-release wording;
- hosted-service, production, package-publication, or private-core-heavy work.

## Research adaptation

Before implementation, a dedicated research/adaptation pass compared the original Phase 11 plan against the current repository and CI best practices. The implementation adapted the plan as follows:

- keep `scripts/alpha_gate.sh` as the operator-local full bundle instead of duplicating it inside CI;
- add CI parity for public readiness, terminology, and whitespace checks where they are cheap and deterministic;
- add pip caching through setup-python rather than introducing a new dependency manager requirement;
- add least-privilege workflow permissions, per-branch concurrency cancellation, matrix fail-fast disabled, and job timeouts;
- add console `.env.example` bootstrap before Vite build for CI robustness;
- create a review policy doc instead of scattering memory-safety rules only across contribution prose.

## Files changed

Phase 11 files:

- `.github/workflows/ci.yml`
- `.github/pull_request_template.md`
- `CONTRIBUTING.md`
- `docs/review-policy.md`
- `CHANGELOG.md`
- `README.md`
- `docs/status/tranched-plan-status.md`
- `docs/status/phase-11-release-operating-discipline-closeout.md`

Phase 10 files remain part of the same landing baseline from the prior completed local implementation:

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

Passed locally before final commit/tag:

```text
PYTHONPATH=src python3 -m pytest -q tests/test_metrics.py tests/test_decay.py tests/test_demo_flow.py
19 passed

PYTHONPATH=src python3 -m pytest -q
890 passed, 27 warnings

python3 scripts/terminology_inventory.py --fail-on-public-stale
PASS

python3 scripts/terminology_inventory.py --fail-on-capitalized-prose
PASS

python3 scripts/public_readiness_check.py
ShyftR public readiness check
PASS

git diff --check
PASS

bash scripts/alpha_gate.sh
ALPHA_GATE_READY
```

## Closeout scope boundary

This artifact records local implementation evidence and the intended planning-baseline tag scope. It does not claim package publication, production readiness, hosted-service readiness, stable release, Checkpoint E, Checkpoint F, or any Phase 12 work.
