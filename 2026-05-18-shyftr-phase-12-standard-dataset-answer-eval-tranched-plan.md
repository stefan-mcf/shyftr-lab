# ShyftR Phase 12 Implementation Plan

> **For Hermes:** Use the ShyftR skill first. Use this plan task-by-task; keep every tranche additive, local-first, and claim-limited.

**Goal:** Extend ShyftR from fixture-level retrieval benchmarking into standard-dataset mapping plus deterministic runner-owned answer evaluation, without automatic large downloads or broad performance claims.

**Architecture:** Phase 12 builds on the Phase 11 benchmark harness. It adds LongMemEval and BEAM as local-path/private-by-default mapping layers, then adds deterministic answerer/judge modules that run above retrieved items so the backend remains the only compared component. Optional LLM judging and scale runs are final-gated extensions, not the default path.

**Tech Stack:** Python dataclasses, repo-local benchmark runner, JSON/JSONL conversion scripts, pytest, existing ShyftR benchmark adapters, static HTML/JSON closeout reporting.

---

## Starting truth

- Starting commit: `bda4817884f3605bed30e9480563df7b6348bc56`
- Phase 11 closeout: `2026-05-17-shyftr-phase-11-final-closeout.md`
- Phase 11 final report: `docs/benchmarks/phase11-final-benchmark-report.html`
- Research basis: `2026-05-18-shyftr-phase-12-deep-research.md`
- Current branch should be `main` and clean before implementation starts.

## Non-negotiable claim and data rules

- No automatic download of LongMemEval, BEAM, or full LOCOMO.
- No committed converted third-party dataset files.
- Treat external benchmark inputs as private-by-default unless a local input explicitly declares public-safe status and the operator requests public output.
- Reports must include `claims_allowed` and `claims_not_allowed`.
- ShyftR should be differentiated on provenance, review gates, auditability, feedback, and reproducible local control, not broad unmeasured superiority.
- Runner-owned answer/judge is the only answer-eval path in this phase by default. Backend-owned answering remains out of scope unless a later explicit experiment asks for it.

## Phase 12 tranche overview

| Tranche | Title | Stop boundary |
|---|---|---|
| P12-0 | Phase 12 kickoff artifacts | Planning only; no code changes beyond docs |
| P12-1 | LongMemEval local mapping scaffold | No dataset download, no full run |
| P12-2 | LongMemEval case-manifest and per-question isolation contract | No backend behavior change beyond fixture/run identity support |
| P12-3 | Deterministic answerer/judge contracts | No external LLM calls |
| P12-4 | Runner integration for deterministic answer-eval | Fixture-only answer results; no standard-dataset claims |
| P12-5 | Retrieval metric completion | Metric math only; no new datasets |
| P12-6 | BEAM local subset mapping scaffold | No large-bucket run |
| P12-7 | Optional LLM judge and local scaling design gate | Planning and gated code path only; no credentials required |
| P12-final | Phase 12 closeout report | HTML/JSON closeout, CI-green, claim-limited |

## P12-0: Kickoff artifacts

**Objective:** Land the research, plan, and handoff artifacts that make Phase 12 executable.

**Files:**

- Create: `2026-05-18-shyftr-phase-12-deep-research.md`
- Create: `2026-05-18-shyftr-phase-12-standard-dataset-answer-eval-tranched-plan.md`
- Create: `2026-05-18-shyftr-phase-12-handoff-packet.md`

**Steps:**

1. Read Phase 11 closeout and benchmark docs.
2. Record external benchmark findings for LOCOMO, LongMemEval, and BEAM.
3. State why LongMemEval mapping is first.
4. State why deterministic answer-eval comes before optional LLM judging.
5. Write the handoff packet with P12-1 as the immediate next tranche.
6. Run terminology and public-readiness checks.

**Verification:**

```bash
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

**Expected:** all pass.

## P12-1: LongMemEval local mapping scaffold

**Objective:** Add a LongMemEval-standard local mapping layer that converts normalized local LongMemEval-style JSON into the existing `BenchmarkFixture` contract.

**Files:**

- Create: `src/shyftr/benchmarks/longmemeval_standard.py`
- Create: `scripts/convert_longmemeval_standard_fixture.py`
- Create: `tests/test_benchmark_longmemeval_standard_mapping.py`
- Create: `docs/benchmarks/p12-1-longmemeval-mapping.md`
- Modify: `src/shyftr/benchmarks/fixture.py`
- Modify: `scripts/run_memory_benchmark.py`
- Modify: `docs/benchmarks/README.md`

**Implementation contract:**

- Accepted normalized shape may include:
  - top-level list of question cases, or object with `cases` / `questions`;
  - per-case fields: `question_id`, `question_type`, `question`, `answer`, `haystack_sessions`, `haystack_dates`, `haystack_session_ids`, `question_date`;
  - session messages with `role`, `content`, and optional `date` / timestamp fields.
- Each LongMemEval case should map into isolated `BenchmarkConversation` objects and one `BenchmarkQuestion`.
- Fixture metadata should preserve case ids and question type labels.
- `contains_private_data` defaults to true unless explicitly false.
- Loader rejects private-marked input unless `allow_private_data=True`.

**Minimal tests:**

- `test_longmemeval_standard_payload_maps_to_fixture_contract`
- `test_longmemeval_standard_loader_rejects_private_by_default`
- `test_resolver_loads_longmemeval_standard_format_from_explicit_path`
- `test_longmemeval_standard_name_requires_explicit_path`
- `test_converter_writes_guarded_public_fixture`
- `test_converter_rejects_private_input_without_override`
- `test_converter_rejects_output_outside_guarded_dirs`

**Focused verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_longmemeval_standard_mapping.py
PYTHONPATH=.:src python scripts/convert_longmemeval_standard_fixture.py \
  --input tmp/longmemeval-smoke.json \
  --output artifacts/benchmarks/longmemeval_smoke.fixture.json \
  --public-output
```

Use a tiny synthetic LongMemEval-shaped file under `tmp/` for the smoke command. Remove `tmp/` before staging.

**Stop boundary:** no automatic download, no full LongMemEval report, no answer-eval, no BEAM work.

## P12-2: LongMemEval case-manifest and per-question isolation contract

**Objective:** Make the per-question haystack shape explicit so future LongMemEval runs do not accidentally leak memory between benchmark cases.

**Files:**

- Modify: `src/shyftr/benchmarks/longmemeval_standard.py`
- Modify: `scripts/convert_longmemeval_standard_fixture.py`
- Modify: `docs/benchmarks/p12-1-longmemeval-mapping.md`
- Modify/Create: `docs/benchmarks/p12-2-longmemeval-case-manifest.md`
- Modify: `tests/test_benchmark_longmemeval_standard_mapping.py`

**Implementation contract:**

- Add a manifest sidecar section with:
  - case count;
  - session count;
  - message count;
  - question-type counts;
  - input/output SHA-256;
  - private/public posture;
  - note that full benchmark execution is not yet claimed.
- Add fixture metadata that marks each case/session isolation boundary.
- Document that future full runs must reset backend state per case unless a specific experiment declares warm shared memory.

**Focused verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_longmemeval_standard_mapping.py
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/public_readiness_check.py
```

**Stop boundary:** no runner architectural change beyond metadata and manifest. Do not run full LongMemEval.

## P12-3: Deterministic answerer and judge contracts

**Objective:** Add zero-cost answerer/judge interfaces and deterministic implementations without touching external LLM APIs.

**Files:**

- Create: `src/shyftr/benchmarks/answerer.py`
- Create: `src/shyftr/benchmarks/judge.py`
- Create: `tests/test_benchmark_answerer_judge.py`
- Modify: `docs/benchmarks/methodology.md`
- Modify: `docs/benchmarks/report-schema.md`

**Implementation contract:**

- `AnswerResult` fields:
  - `answer_text`
  - `answer_state`: `answered`, `abstained_unknown`, or `abstained_insufficient`
  - `supporting_item_ids`
  - `latency_ms`
  - optional token/cost fields defaulting to zero/none.
- Deterministic answerers:
  - `ExtractiveAnswerer`: answers from retrieved text using simple string/keyword support where possible;
  - `FixedLabelAnswerer`: oracle/debug answerer that returns expected labels only for calibration and must be clearly marked as non-comparable.
- `JudgeResult` fields:
  - score;
  - verdict label;
  - evaluation type;
  - notes.
- Deterministic judges:
  - exact normalized match;
  - token-F1 / fuzzy match;
  - composite deterministic judge.

**Focused verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_answerer_judge.py
PYTHONPATH=.:src pytest -q tests/test_benchmark_adapter_contract.py tests/test_benchmark_locomo_mini_fixture.py
```

**Stop boundary:** no runner integration and no external LLM calls.

## P12-4: Runner integration for deterministic answer-eval

**Objective:** Add an opt-in deterministic answer-eval path to the runner and CLI for fixture-level runs.

**Files:**

- Modify: `src/shyftr/benchmarks/runner.py`
- Modify: `scripts/run_memory_benchmark.py`
- Modify: `src/shyftr/benchmarks/report.py` if the current report dataclasses need structured answer fields
- Modify: `tests/test_benchmark_locomo_mini_fixture.py`
- Modify/Create: `tests/test_benchmark_answerer_judge.py`
- Modify: `docs/benchmarks/README.md`
- Modify: `docs/benchmarks/report-schema.md`

**Implementation contract:**

- Add CLI flags:
  - `--enable-answer-eval`
  - `--answerer deterministic-extractive|fixed-label-debug`
  - `--judge deterministic-composite`
- Default remains disabled to preserve Phase 11 behavior.
- Report must disclose answerer and judge names.
- Answer metrics must include:
  - correctness;
  - token-F1 when available;
  - abstention rate;
  - correct abstention rate;
  - missed-answer rate;
  - hallucination-like unsupported-answer rate;
  - by-question-type breakdown.

**Focused verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_answerer_judge.py tests/test_benchmark_locomo_mini_fixture.py
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture locomo-mini \
  --run-id p12-answer-eval-smoke \
  --output artifacts/benchmarks/p12_answer_eval_smoke.json \
  --top-k 1,3,5 \
  --enable-answer-eval
```

**Stop boundary:** fixture-level answer-eval only. Do not claim full standard-dataset answer quality.

## P12-5: Retrieval metric completion

**Objective:** Implement methodology-promised retrieval/control metrics that are currently documented but missing.

**Files:**

- Modify: `src/shyftr/benchmarks/runner.py`
- Create/Modify: `tests/test_benchmark_metrics.py`
- Modify: `docs/benchmarks/report-schema.md`
- Modify: `docs/benchmarks/methodology.md`

**Implementation contract:**

- Add nDCG computation to retrieval metrics.
- Add answer-support coverage using expected item ids and deterministic answer support where available.
- Add conflict/stale retrieval rate only when fixture metadata supplies enough labels; otherwise report `not_supported`.
- Keep unavailable control/audit metrics explicit as `not_supported` or `not_run`.

**Focused verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_metrics.py tests/test_benchmark_locomo_mini_fixture.py
```

**Stop boundary:** metric math only. No new dataset mapping.

## P12-6: BEAM local subset mapping scaffold

**Objective:** Add BEAM-standard local subset mapping for operator-provided files, without running large buckets.

**Files:**

- Create: `src/shyftr/benchmarks/beam_standard.py`
- Create: `scripts/convert_beam_standard_fixture.py`
- Create: `tests/test_benchmark_beam_standard_mapping.py`
- Create: `docs/benchmarks/p12-6-beam-mapping.md`
- Modify: `src/shyftr/benchmarks/fixture.py`
- Modify: `scripts/run_memory_benchmark.py`
- Modify: `docs/benchmarks/README.md`

**Implementation contract:**

- Accept a normalized local subset shape first.
- Preserve BEAM ability type in `question_type`.
- Add sidecar manifest with row/case counts, question counts, token-bucket label if provided, and license note.
- Default to private-by-default unless public-safe is explicitly declared.

**Focused verification:**

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_beam_standard_mapping.py
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/public_readiness_check.py
```

**Stop boundary:** no full BEAM run and no 10M-token bucket attempt.

## P12-7: Optional LLM judge and local scaling design gate

**Objective:** Prepare optional LLM judge and scaling designs without making credentials or large local runs required.

**Files:**

- Create: `docs/benchmarks/p12-7-optional-llm-judge-and-scaling.md`
- Optionally create later code only after deterministic answer-eval is green:
  - `src/shyftr/benchmarks/llm_judge.py`
  - `tests/test_benchmark_llm_judge.py`

**Required design decisions before code:**

- Which provider interface is allowed?
- How are model name, prompt version, temperature, and token cost recorded?
- What exact skip behavior occurs when credentials are absent?
- What local output directories are allowed for private scaling reports?
- What report wording prevents public answer-quality overclaiming?

**Stop boundary:** no credential use, no paid API calls, and no long scaling run without explicit approval.

## P12-final: Closeout and polished report

**Objective:** Close Phase 12 with the same standard as Phase 11.

**Files:**

- Create: `2026-05-18-shyftr-phase-12-final-closeout.md`
- Create: `docs/benchmarks/phase12-final-benchmark-report.html`
- Create: `docs/benchmarks/phase12-final-benchmark-report.json`
- Create/Modify: `scripts/phase12_final_benchmark_report.py`
- Commit any public-safe fixture-level reports under `reports/benchmarks/`

**Closeout report must separate:**

- measured fixture retrieval metrics;
- measured fixture answer-eval metrics;
- LongMemEval mapping/conversion readiness;
- BEAM mapping/conversion readiness;
- optional or skipped comparators;
- claims not allowed.

**Full verification gate:**

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_adapter_contract.py tests/test_benchmark_locomo_mini_fixture.py tests/test_benchmark_locomo_standard_mapping.py tests/test_benchmark_phase11_final_report.py tests/test_benchmark_longmemeval_standard_mapping.py tests/test_benchmark_answerer_judge.py tests/test_benchmark_metrics.py tests/test_benchmark_beam_standard_mapping.py
PYTHONPATH=.:src pytest -q
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

If some later tranche tests do not exist yet, omit only those specific file names until the tranche creates them. Do not omit full-suite, terminology, public-readiness, or whitespace checks at closeout.

## Commit policy

- P12-0 can be one docs-only commit.
- Each implementation tranche should be its own commit after focused tests pass.
- Do not combine LongMemEval mapping, answer-eval, and BEAM mapping in one commit.
- Push and verify GitHub checks after each tranche that changes code.

## First execution command matrix

Before starting P12-1:

```bash
cd /Users/stefan/ShyftR
git status --short --branch
git log --oneline -3
python scripts/public_readiness_check.py
```

Then begin with:

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_locomo_standard_mapping.py
```

This confirms the existing mapping/converter pattern before adding the LongMemEval analogue.
