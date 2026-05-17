# ShyftR Phase 13 implementation plan: local full-dataset runbook and optional judge gating

> **For Hermes:** Use the ShyftR skill first. Use this plan task-by-task. Keep Phase 13 local-first, operator-approved, private-by-default, and claim-limited. Do not download datasets, use credentials, call paid APIs, or publish third-party-derived artifacts unless an explicit human approval step says so.

**Goal:** Make ShyftR ready for approved local full-dataset benchmark runs by adding a contract-first runbook, safe dry-run controls, per-case reset support, and optional LLM judge gating without performing full runs or public summaries in this phase slice.

**Architecture:** Phase 13 builds on the completed Phase 12 benchmark scaffolds. P13-0 creates the operator runbook and approval checklist, P13-1 adds runner controls needed to validate local standard-dataset files safely before a full run, and P13-2 implements optional LLM judge gating as skip-safe scaffolding while preserving deterministic judging as the default.

**Tech stack:** Python benchmark runner, repo-local conversion helpers, pytest, JSON/JSONL reports, static benchmark docs, optional OpenAI-compatible judge provider interface with no required dependency.

---

## Starting truth

- Repo: `/Users/stefan/ShyftR`
- Starting branch: `main`
- Starting HEAD: `db911a1` (`docs: mark phase 12 ci green`)
- Phase 12 closeout: `2026-05-18-shyftr-phase-12-final-closeout.md`
- Phase 13 research: `2026-05-18-shyftr-phase-13-deep-research.md`
- Phase 12 completed:
  - LongMemEval local-path/private-by-default mapper and guarded converter.
  - BEAM local-path/private-by-default mapper and guarded converter.
  - Deterministic runner-owned answerer/judge and opt-in `--enable-answer-eval`.
  - Retrieval metrics including nDCG and answer-support coverage.
- Phase 12 did not run full LongMemEval, BEAM, or LOCOMO. Phase 13 must not imply those results exist.

## Non-negotiable data, cost, and claim rules

1. No automatic dataset downloads.
2. No credentials, paid APIs, or optional LLM calls during default verification.
3. No full standard-dataset run during P13-0/P13-1/P13-2 implementation unless the operator explicitly supplies a local dataset path and approves a private run.
4. Treat all operator-provided standard-dataset files as private by default.
5. Do not commit converted third-party datasets, private reports, raw judge logs, or dataset-derived text.
6. Outputs from local/private runs must stay under `artifacts/`, `reports/`, or `tmp/` and must be reviewed before any commit.
7. BEAM-derived reports require CC BY-SA 4.0 attribution and share-alike notice if any result artifact is shared.
8. Deterministic answer evaluation remains the default. Optional LLM judging is supplementary and must disclose model, prompt version/hash, temperature, token counts, cost estimate, and skip reason when unavailable.
9. Excluded from this plan: public summary generation or publication. Do not add a Phase 13 public summary tranche here.

## Deep-research hardening conclusions

- LongMemEval is the best first local full-dataset target because it has 500 evaluation instances, a clear per-question haystack shape, MIT licensing, and upstream answer-eval prompts that can inform optional judge design.
- LongMemEval full runs require per-case reset semantics: each question's haystack sessions should be ingested, searched, then cleared unless an experiment explicitly declares shared warm memory.
- LongMemEval S-cleaned is the recommended first operator-approved full split; M-cleaned is a later stress path; oracle is useful for diagnostic retrieval/answer separation.
- BEAM is useful but riskier operationally because it is larger, split by token scale, and CC BY-SA 4.0. Phase 13 should support its local runbook and dry-run validation but should not start with large BEAM buckets.
- LLM-as-judge work must account for known judge biases: position bias, verbosity bias, self-preference, and weak multi-step reasoning. ShyftR should record deterministic-vs-LLM agreement and keep deterministic metrics primary.
- The current runner ingests all fixture conversations and then searches all questions. That is fine for tiny public fixtures, but not enough for LongMemEval-style per-case runs.
- The current CLI resolver supports BEAM through `--fixture-path --fixture-format beam-standard`, but `run_memory_benchmark.py` choices need to include `beam-standard` for a clean operator experience.
- The runner needs a bounded dry-run selector such as `--limit-questions N` before any full local runbook is practical.

## Phase 13 tranche overview

| Tranche | Title | Stop boundary |
|---|---|---|
| P13-0 | Contract-first local full-dataset runbook | Docs and validation contract only; no dataset download, no code required unless correcting docs/examples |
| P13-1 | Dry-run and per-case reset runner controls | Code supports safe local dry-runs; no full standard-dataset run is performed by default |
| P13-2 | Optional LLM judge gating scaffold | Skip-safe provider scaffolding and tests only; no real credentials or paid calls |

No public-summary tranche is included in this plan.

---

## P13-0: Contract-first local full-dataset runbook

**Objective:** Create the canonical private/local operator runbook and approval checklist for LongMemEval, BEAM, and LOCOMO-standard runs, without downloading data or running full datasets.

**Files:**

- Create: `docs/benchmarks/phase13-local-full-dataset-runbook.md`
- Modify: `docs/benchmarks/README.md` only to link the runbook and preserve claim boundaries.
- Read first:
  - `2026-05-18-shyftr-phase-12-final-closeout.md`
  - `2026-05-18-shyftr-phase-13-deep-research.md`
  - `docs/benchmarks/p12-1-longmemeval-mapping.md`
  - `docs/benchmarks/p12-2-longmemeval-case-manifest.md`
  - `docs/benchmarks/p12-6-beam-mapping.md`
  - `docs/benchmarks/p12-7-optional-llm-judge-and-scaling.md`
  - `scripts/convert_longmemeval_standard_fixture.py`
  - `scripts/convert_beam_standard_fixture.py`
  - `scripts/convert_locomo_standard_fixture.py`
  - `scripts/run_memory_benchmark.py`

**Runbook content requirements:**

1. State that the runbook is for operator-provided local files only.
2. Use placeholders such as `<LOCAL_LONGMEMEVAL_JSON>` and `<LOCAL_BEAM_JSON>` instead of live download commands.
3. Include a top-level approval checklist:
   - local dataset path exists outside committed repo content or under ignored scratch area;
   - license reviewed;
   - `contains_private_data` posture declared;
   - private output path chosen;
   - dry-run limit chosen;
   - timeout/retry/resume settings chosen;
   - optional LLM judge disabled unless explicitly approved;
   - no public summary/public commit intended.
4. Include exact conversion commands for:
   - LongMemEval local JSON -> guarded fixture;
   - BEAM local JSON/JSONL -> guarded fixture;
   - LOCOMO-standard local JSON -> guarded fixture.
5. Include exact dry-run commands using planned P13-1 flags, clearly marked as requiring P13-1 implementation before use:
   - `--limit-questions 5`
   - `--isolate-per-case`
   - `--allow-private-fixture`
   - `--enable-answer-eval`
   - `--resume-existing`
6. Include private full-run command templates, but mark them `operator-approved only` and do not claim they were run.
7. Include BEAM CC BY-SA 4.0 attribution requirements for any shared BEAM-derived artifact.
8. Include report interpretation rules:
   - fixture-level vs standard-dataset local run;
   - deterministic answer-eval vs optional LLM judge;
   - skipped/failed/timeout statuses;
   - allowed and disallowed claims.
9. Include generated-artifact hygiene:
   - private converted fixtures and run reports are not committed by default;
   - public-safe fixture-level reports may only be committed after review;
   - raw LLM judgment JSONL is private unless explicitly scrubbed/reviewed.

**Verification:**

```bash
cd /Users/stefan/ShyftR
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

**Expected:** all pass.

**Stop boundary:** Do not download any dataset, create converted third-party fixtures, run full datasets, use credentials, or generate public summaries.

---

## P13-1: Dry-run and per-case reset runner controls

**Objective:** Add runner controls that make the P13-0 runbook executable safely on operator-provided local files: bounded question selection, per-case reset, clean BEAM CLI routing, and report metadata proving the safety posture.

**Files:**

- Modify: `src/shyftr/benchmarks/runner.py`
- Modify: `scripts/run_memory_benchmark.py`
- Modify: `docs/benchmarks/phase13-local-full-dataset-runbook.md`
- Modify: `docs/benchmarks/README.md`
- Modify: `docs/benchmarks/report-schema.md`
- Create: `tests/test_benchmark_phase13_runner_controls.py`

**Implementation contract:**

1. Add runner parameters:
   - `limit_questions: Optional[int] = None`
   - `isolate_per_case: bool = False`
2. Add CLI flags:
   - `--limit-questions N`; positive integer; limits the run to the first N questions after fixture load.
   - `--isolate-per-case`; when enabled, each question is run with only its case conversations and backend state reset before that question.
3. Add `beam-standard` to `--fixture` and `--fixture-format` choices where appropriate. The name-based `beam-standard` selector must still require explicit `--fixture-path` and must not download anything.
4. Report safety metadata in `fairness` or `runner.environment_notes`, including:
   - `limit_questions`
   - `limited_question_count`
   - `isolate_per_case`
   - `case_group_metadata_key` if used
   - reset/ingest/search operation counts when easy to expose
5. Per-case reset grouping rules:
   - For LongMemEval, use `BenchmarkConversation.metadata["isolation_group"]` and `BenchmarkQuestion.evaluation_notes`/question id to bind question to conversations.
   - If a question has no group metadata, default to its expected item ids or question id only when unambiguous; otherwise return a clear failed/skipped backend result rather than silently running shared-state mode.
   - Do not introduce a shared warm-memory mode in P13-1.
6. Preserve backward compatibility:
   - default behavior remains the Phase 12 serial fixture run;
   - no existing public fixture output shape breaks;
   - `--enable-answer-eval` still works with and without `--limit-questions`.
7. Dry-run contract:
   - `--limit-questions 5 --isolate-per-case` is the recommended preflight for LongMemEval S-cleaned;
   - dry-run reports must not be described as full benchmark results.

**Minimal RED tests:**

Create `tests/test_benchmark_phase13_runner_controls.py` with tests equivalent to:

- `test_limit_questions_runs_bounded_subset_and_reports_limit`
- `test_isolate_per_case_resets_backend_before_each_question`
- `test_isolate_per_case_ingests_only_matching_case_conversations`
- `test_isolate_per_case_fails_or_skips_when_case_group_is_missing`
- `test_cli_accepts_beam_standard_explicit_path_format_without_download`
- `test_defaults_preserve_phase12_shared_fixture_behavior`
- `test_answer_eval_still_runs_with_limit_questions`

Use tiny synthetic fixtures in the test file. Do not use third-party data.

**Focused verification:**

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_phase13_runner_controls.py
PYTHONPATH=.:src pytest -q tests/test_benchmark_longmemeval_standard_mapping.py tests/test_benchmark_beam_standard_mapping.py tests/test_benchmark_answerer_judge.py tests/test_benchmark_metrics.py tests/test_benchmark_locomo_standard_mapping.py tests/test_benchmark_locomo_mini_fixture.py tests/test_benchmark_adapter_contract.py tests/test_benchmark_phase11_final_report.py
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

**Full gate before P13-1 closeout:**

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src pytest -q
```

**Stop boundary:** Do not run full LongMemEval/BEAM/LOCOMO, do not download datasets, do not add optional LLM calls, and do not generate a public summary.

---

## P13-2: Optional LLM judge gating scaffold

**Objective:** Implement the optional LLM judge gate from P12-7 as explicit, skip-safe scaffolding. The code must prove that missing credentials/dependencies produce a structured skip and that deterministic judging remains primary.

**Files:**

- Create: `src/shyftr/benchmarks/llm_judge.py`
- Create: `tests/test_benchmark_llm_judge.py`
- Create: `docs/benchmarks/phase13-optional-llm-judge-gating.md`
- Modify: `src/shyftr/benchmarks/runner.py`
- Modify: `scripts/run_memory_benchmark.py`
- Modify: `docs/benchmarks/methodology.md`
- Modify: `docs/benchmarks/report-schema.md`
- Modify: `docs/benchmarks/phase13-local-full-dataset-runbook.md`
- Modify: `docs/benchmarks/README.md`

**Implementation contract:**

1. Add an optional judge provider abstraction without adding a required dependency.
2. CLI flags:
   - `--llm-judge-provider none|openai-compatible|local-openai-compatible` (default `none`)
   - `--llm-judge-model <model>`
   - `--llm-judge-base-url <url>` for local/OpenAI-compatible endpoints
   - `--llm-judge-api-key-env <ENV_NAME>` or `--llm-judge-api-key-file <PATH>`; do not accept raw API keys on the command line if avoidable
   - `--llm-judge-max-retries N`
   - `--llm-judge-output-jsonl artifacts|reports|tmp path`
3. Credential posture:
   - Provider is never inferred from ambient credentials.
   - If provider is `none`, no import, no network, and no skip noise.
   - If provider is requested and package/endpoint/key is missing, report `skipped` with reason.
   - Do not serialize secrets into report JSON or logs.
4. Judge behavior:
   - deterministic composite judge always runs first;
   - optional LLM judge is supplementary and may add `llm_judge` metrics/details;
   - record deterministic-vs-LLM agreement when both are available;
   - temperature fixed at 0 for all judge calls;
   - prompt template version/hash recorded.
5. Prompt design:
   - provide LongMemEval-style binary yes/no templates per question family;
   - include abstention-specific prompt handling;
   - include a generic fallback prompt for unknown question types;
   - keep templates in code or docs with stable version identifiers.
6. Cost/latency metadata:
   - token counts if provider returns usage;
   - deterministic token estimate if usage is absent;
   - cost estimate only when model pricing is explicitly known/configured, otherwise `unknown`.
7. Output posture:
   - raw LLM judgment JSONL is written only under guarded local directories;
   - default tests must not create real network calls;
   - generated judge logs are not committed by default.

**Minimal RED tests:**

Create `tests/test_benchmark_llm_judge.py` with tests equivalent to:

- `test_llm_judge_provider_none_makes_no_import_or_network_call`
- `test_llm_judge_requested_without_dependency_reports_skipped`
- `test_llm_judge_requested_without_credentials_reports_skipped`
- `test_llm_judge_refuses_to_serialize_api_key`
- `test_llm_judge_requires_guarded_output_path_for_raw_jsonl`
- `test_deterministic_judge_remains_primary_when_llm_judge_is_enabled`
- `test_llm_judge_records_model_prompt_temperature_and_skip_reason`
- `test_llm_judge_agreement_metric_is_reported_when_mock_provider_returns_labels`

Use a fake/mock provider for all positive-path tests. No real OpenAI/vLLM call is allowed.

**Focused verification:**

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_llm_judge.py
PYTHONPATH=.:src pytest -q tests/test_benchmark_phase13_runner_controls.py tests/test_benchmark_answerer_judge.py tests/test_benchmark_metrics.py
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

**Full gate before P13-2 closeout:**

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src pytest -q
```

**Stop boundary:** Do not use real credentials, do not make paid or remote judge calls, do not run full datasets, do not promote LLM judge metrics above deterministic metrics, and do not generate a public summary.

---

## P13 closeout requirements for this plan slice

If P13-0 through P13-2 are implemented, create a local closeout such as:

```text
2026-05-18-shyftr-phase-13-p13-0-to-p13-2-closeout.md
```

The closeout must state:

- exact files changed;
- exact tests/gates run and exit codes;
- whether any dataset was downloaded; expected answer for this plan slice: no;
- whether any full standard dataset was run; expected answer unless explicitly approved later: no;
- whether any credential or paid API was used; expected answer for default verification: no;
- whether optional judge behavior was only mock/skip-safe;
- generated private artifact paths, if any, and whether they are intentionally uncommitted;
- next recommended step after P13-2.

Do not add a public summary/publication artifact as part of this plan.

## Final verification matrix for P13-0..P13-2

Run after the last implemented tranche:

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_phase13_runner_controls.py tests/test_benchmark_llm_judge.py tests/test_benchmark_longmemeval_standard_mapping.py tests/test_benchmark_beam_standard_mapping.py tests/test_benchmark_answerer_judge.py tests/test_benchmark_metrics.py tests/test_benchmark_locomo_standard_mapping.py tests/test_benchmark_locomo_mini_fixture.py tests/test_benchmark_adapter_contract.py tests/test_benchmark_phase11_final_report.py
PYTHONPATH=.:src pytest -q
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

## Commit policy

- P13-0 may be a docs-only commit.
- P13-1 should be a separate code+docs commit after focused and full gates pass.
- P13-2 should be a separate code+docs commit after focused and full gates pass.
- Push and verify GitHub CI only after the user approves push or asks to proceed through closeout.
- Never include private converted fixtures, private full-run reports, raw judge logs, credentials, or downloaded datasets in commits.

## Immediate first execution command matrix

Before starting P13-0 implementation:

```bash
cd /Users/stefan/ShyftR
git status --short --branch
git log --oneline -5
python scripts/public_readiness_check.py
```

Then create the P13-0 runbook and link it from benchmark README.
