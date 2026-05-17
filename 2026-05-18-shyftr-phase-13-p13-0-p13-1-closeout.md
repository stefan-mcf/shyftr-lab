# ShyftR Phase 13 P13-0/P13-1 closeout

Date: 2026-05-18
UTC verification timestamp: 2026-05-17T21:16:44Z
Repo: `/Users/stefan/ShyftR`
Branch: `main`
Starting HEAD: `db911a1` (`docs: mark phase 12 ci green`)
Status: P13-0 and P13-1 complete locally; ready for P13-2 implementation.

## Scope completed

P13-0: contract-first local full-dataset runbook.

P13-1: dry-run and per-case reset runner controls.

Public summary/publication work remains excluded. Optional LLM judge gating is not implemented in this slice and is the next tranche, P13-2.

## Files changed or created

Created:

- `docs/benchmarks/phase13-local-full-dataset-runbook.md`
- `tests/test_benchmark_phase13_runner_controls.py`
- `2026-05-18-shyftr-phase-13-p13-0-p13-1-closeout.md`

Modified:

- `src/shyftr/benchmarks/runner.py`
- `scripts/run_memory_benchmark.py`
- `docs/benchmarks/README.md`
- `docs/benchmarks/methodology.md`
- `docs/benchmarks/report-schema.md`
- `2026-05-18-shyftr-phase-13-handoff-packet.md`

Pre-existing Phase 13 planning artifacts retained untracked in the worktree:

- `2026-05-18-shyftr-phase-13-deep-research.md`
- `2026-05-18-shyftr-phase-13-local-full-dataset-runbook-judge-gating-plan.md`
- `2026-05-18-shyftr-phase-13-handoff-packet.md`

## Implementation summary

Runner and CLI controls:

- Added `--limit-questions N` with positive-integer validation.
- Added `--isolate-per-case` for per-question backend reset and case-scoped ingest.
- Added `beam-standard` to CLI fixture and fixture-format choices so explicit local BEAM paths fail cleanly or load without any download path.
- Added fairness/report metadata:
  - `limit_questions`
  - `original_question_count`
  - `limited_question_count`
  - `isolate_per_case`
  - `case_group_metadata_key`
  - backend reset, ingest, and search operation counts.
- Preserved default Phase 12 shared-fixture behavior when new flags are absent.
- Preserved deterministic answer evaluation with `--limit-questions`.

Docs:

- Added the canonical private/local operator runbook with approval checklist, conversion templates, dry-run templates, private full-run templates, report interpretation rules, artifact hygiene, and BEAM CC BY-SA 4.0 notice.
- Linked the runbook from benchmark README.
- Updated methodology and report-schema docs for Phase 13 local-run controls.

Tests:

- Added focused synthetic tests for question limiting, per-case reset counts, case-scoped ingest, missing case-group failures, BEAM CLI/direct local routing, default compatibility, and answer-eval with question limits.

## Verification performed

Focused and gate commands run from repo root:

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_phase13_runner_controls.py
PYTHONPATH=.:src pytest -q tests/test_benchmark_longmemeval_standard_mapping.py tests/test_benchmark_beam_standard_mapping.py tests/test_benchmark_answerer_judge.py tests/test_benchmark_metrics.py tests/test_benchmark_locomo_standard_mapping.py tests/test_benchmark_locomo_mini_fixture.py tests/test_benchmark_adapter_contract.py tests/test_benchmark_phase11_final_report.py
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

Result: exit 0.

Observed focused test output:

```text
8 passed in 0.31s
37 passed in 1.55s
ShyftR public readiness check
PASS
```

Full regression command:

```bash
PYTHONPATH=.:src pytest -q
```

Result: exit 0.

Observed full-suite output:

```text
1140 passed, 40 warnings in 21.00s
```

Smoke validation:

- A tiny synthetic LongMemEval-style local JSON was created under `tmp/benchmarks/`.
- It was run through direct `--fixture-format longmemeval-standard` with `--limit-questions 1 --isolate-per-case --enable-answer-eval`.
- The report assertions confirmed bounded question count, per-case reset mode, and reset count metadata.
- The smoke input, report, and temporary benchmark cell were removed before closeout.

## Data, credential, and artifact posture

- Dataset downloaded: no.
- Full LongMemEval, BEAM, or LOCOMO run performed: no.
- Third-party dataset converted: no.
- Credentials used: no.
- Paid or remote API called: no.
- Optional LLM judge implemented or called: no.
- Private/generated smoke artifacts left behind: no.
- Public summary generated: no.

## Claim boundary

P13-0/P13-1 make the harness ready for bounded local validation on operator-provided files. They do not establish full standard-dataset scores and do not support public benchmark superiority claims.

## Ready for P13-2

Next tranche: optional LLM judge gating scaffold.

Expected P13-2 start files:

- `src/shyftr/benchmarks/llm_judge.py`
- `tests/test_benchmark_llm_judge.py`
- `docs/benchmarks/phase13-optional-llm-judge-gating.md`

P13-2 guardrails:

- deterministic judge remains primary;
- provider defaults to none;
- no ambient credential inference;
- missing dependency/credential produces structured skip;
- no raw API keys serialized into reports/logs;
- tests must use mock providers only;
- no full datasets, downloads, paid calls, credentials, or public summaries without explicit approval.
