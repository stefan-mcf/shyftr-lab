# Phase 13 local full-dataset runbook

Status: P13-0/P13-1 operator runbook. This document does not claim that any full standard dataset has been run.

## Scope

This runbook describes how an operator can prepare and validate local standard-dataset benchmark runs after supplying approved local dataset files. It is private-by-default and claim-limited.

Covered formats:

- `locomo-standard`
- `longmemeval-standard`
- `beam-standard`

Not covered in P13-0/P13-1:

- automatic dataset download;
- credentials or paid API use;
- optional LLM judging;
- public summary generation;
- publishing converted third-party artifacts.

## Approval checklist before using local data

Before converting or running any third-party dataset file, confirm all items below:

- [ ] The dataset file already exists locally and was obtained with explicit operator approval.
- [ ] The local dataset file is outside committed repo content, or in an ignored scratch location.
- [ ] The dataset license has been reviewed.
- [ ] `contains_private_data` posture is known; if unsure, treat it as private.
- [ ] Output path is under `artifacts/`, `reports/`, or `tmp/`.
- [ ] Dry-run size is chosen, normally `--limit-questions 5`.
- [ ] Timeout, retry, and resume settings are chosen.
- [ ] Optional LLM judge is disabled for P13-0/P13-1.
- [ ] No public summary, public commit, or publication is intended from the private run.

Human approval is still required before downloading data, using credentials, running paid or remote judges, sharing BEAM-derived results, publishing summaries, or committing converted third-party artifacts.

## Output hygiene

Use these directories only:

```text
artifacts/benchmarks/
reports/benchmarks/
tmp/benchmarks/
```

Private converted fixtures, private run reports, and raw judge logs are not committed by default. Review any generated artifact before staging.

## Convert approved local files

Use placeholders for local files. Do not replace these with live download commands inside repo docs.

### LongMemEval local file

```bash
PYTHONPATH=.:src python scripts/convert_longmemeval_standard_fixture.py \
  --input <LOCAL_LONGMEMEVAL_JSON> \
  --output artifacts/benchmarks/<RUN_ID>.longmemeval.fixture.json
  --allow-private-input
```

For public-safe fixture conversion only, the local input must explicitly declare `contains_private_data: false`, and the command must use `--public-output`. Do not use `--public-output` for normal local full-dataset validation.

### BEAM local file

```bash
PYTHONPATH=.:src python scripts/convert_beam_standard_fixture.py \
  --input <LOCAL_BEAM_JSON_OR_JSONL> \
  --output artifacts/benchmarks/<RUN_ID>.beam.fixture.json
  --allow-private-input
```

BEAM has CC BY-SA 4.0 obligations. Any shared BEAM-derived artifact must include attribution and compatible license notice. P13-0/P13-1 do not approve sharing.

### LOCOMO-standard local file

```bash
PYTHONPATH=.:src python scripts/convert_locomo_standard_fixture.py \
  --input <LOCAL_LOCOMO_JSON_OR_JSONL> \
  --output artifacts/benchmarks/<RUN_ID>.locomo.fixture.json
  --allow-private-input
```

Each converter writes a default sidecar manifest at `<output>.manifest.json` unless `--no-manifest` is used for scratch debugging. Converted fixture outputs use the canonical `shyftr-fixture` report input format; use `locomo-standard`, `longmemeval-standard`, or `beam-standard` only when running directly from an unconverted normalized local file.

## Dry-run validation commands

P13-1 adds the runner controls used below:

- `--limit-questions N`
- `--isolate-per-case`
- clean `beam-standard` CLI routing

### LongMemEval dry run

Use per-case reset for LongMemEval-style question haystacks.

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture-path artifacts/benchmarks/<RUN_ID>.longmemeval.fixture.json \
  --fixture-format shyftr-fixture \
  --run-id <RUN_ID>-longmemeval-dryrun \
  --output artifacts/benchmarks/<RUN_ID>-longmemeval-dryrun.json \
  --top-k 1,3,5,10 \
  --limit-questions 5 \
  --isolate-per-case \
  --timeout-seconds 300 \
  --max-retries 2 \
  --resume-existing \
  --enable-answer-eval \
  --allow-private-fixture
```

Expected proof points:

- report `dataset.question_count` equals the dry-run limit;
- `fairness.limit_questions` is set;
- `fairness.isolate_per_case` is true;
- each backend result reports reset, ingest, and search operation counts;
- `metrics.answer_eval.enabled` is true when answer eval is requested;
- no full-dataset claim is made.

### BEAM dry run

Start with the smallest approved local BEAM file or subset. Do not use BEAM-10M in P13-0/P13-1.

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture-path artifacts/benchmarks/<RUN_ID>.beam.fixture.json \
  --fixture-format shyftr-fixture \
  --run-id <RUN_ID>-beam-dryrun \
  --output artifacts/benchmarks/<RUN_ID>-beam-dryrun.json \
  --top-k 1,3,5,10 \
  --limit-questions 5 \
  --timeout-seconds 300 \
  --max-retries 2 \
  --resume-existing \
  --enable-answer-eval \
  --allow-private-fixture
```

Use `--isolate-per-case` only when the BEAM fixture contains per-case grouping metadata supported by the runner.

### LOCOMO-standard dry run

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture-path artifacts/benchmarks/<RUN_ID>.locomo.fixture.json \
  --fixture-format shyftr-fixture \
  --run-id <RUN_ID>-locomo-dryrun \
  --output artifacts/benchmarks/<RUN_ID>-locomo-dryrun.json \
  --top-k 1,3,5,10 \
  --limit-questions 5 \
  --timeout-seconds 300 \
  --max-retries 2 \
  --resume-existing \
  --enable-answer-eval \
  --allow-private-fixture
```

## Operator-approved private full-run templates

These templates are not executed by default. Use them only after dry-run validation passes and the operator approves a private full run.

LongMemEval private local run:

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture-path artifacts/benchmarks/<RUN_ID>.longmemeval.fixture.json \
  --fixture-format shyftr-fixture \
  --run-id <RUN_ID>-longmemeval-private \
  --output reports/benchmarks/<RUN_ID>-longmemeval-private.json \
  --top-k 1,3,5,10 \
  --isolate-per-case \
  --timeout-seconds 300 \
  --max-retries 2 \
  --resume-existing \
  --enable-answer-eval \
  --allow-private-fixture
```

BEAM private local run:

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture-path artifacts/benchmarks/<RUN_ID>.beam.fixture.json \
  --fixture-format shyftr-fixture \
  --run-id <RUN_ID>-beam-private \
  --output reports/benchmarks/<RUN_ID>-beam-private.json \
  --top-k 1,3,5,10 \
  --timeout-seconds 300 \
  --max-retries 2 \
  --resume-existing \
  --enable-answer-eval \
  --allow-private-fixture
```

## Report interpretation rules

Allowed after a dry run:

- The harness loaded an operator-provided local fixture.
- The runner executed a bounded subset using the recorded configuration.
- The report records deterministic fixture/local-run metrics under the stated top-k, timeout, retry, resume, and reset settings.

Not allowed after a dry run:

- A full LongMemEval, BEAM, or LOCOMO result claim.
- Broad performance or superiority claims.
- Public task-success claims.
- Claims that omit skipped backends, timeout failures, or missing optional dependencies.

For local private full runs, claims still must name the dataset, split, git SHA, run id, top-k values, timeout/retry/resume settings, reset mode, answerer, judge, backend list, and skipped/failed backends.

## BEAM attribution block

Any shared BEAM-derived artifact must include a block equivalent to:

```text
This artifact uses data derived from BEAM (CC BY-SA 4.0).
Dataset: https://huggingface.co/datasets/Mohammadta/BEAM
Attribution: Mohammadta/BEAM contributors.
Derivative sharing must follow CC BY-SA 4.0 obligations.
```

P13-0/P13-1 do not approve sharing BEAM-derived artifacts.

## P13-2 ready optional judge command

Optional LLM judging is disabled by default. To test skip-safe configuration without credentials, keep `--enable-answer-eval` on and request a provider with a missing key variable:

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture locomo-mini \
  --run-id <RUN_ID>-llm-judge-skip \
  --output artifacts/benchmarks/<RUN_ID>-llm-judge-skip.json \
  --top-k 1,3,5 \
  --enable-answer-eval \
  --llm-judge-provider openai-compatible \
  --llm-judge-model <MODEL_NAME> \
  --llm-judge-api-key-env <ENV_NAME>
```

A missing key or optional dependency should produce `metrics.llm_judge.status = skipped`, not a failed backend. Use real credentials, key files, remote endpoints, or raw JSONL output only after explicit operator approval. Raw judge JSONL must be written under `artifacts/`, `reports/`, or `tmp/` and end in `.jsonl`.

## P13-2 preparation

P13-2 adds optional LLM judge gating as explicit, skip-safe scaffolding. Keep deterministic `--enable-answer-eval` primary; optional LLM judging is supplementary and must not infer providers or credentials from ambient environment.
