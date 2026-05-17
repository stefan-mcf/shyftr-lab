# Phase 13 optional LLM judge gating

Status: P13-2 scaffold. Deterministic runner-owned judging remains primary.

## Purpose

P13-2 adds optional LLM-as-judge support for local benchmark experiments. The feature is explicit, skip-safe, and supplementary. Default verification does not import provider SDKs, infer credentials, make network calls, or spend money.

## Default posture

Default CLI behavior:

```text
--llm-judge-provider none
```

With provider `none`:

- no SDK import is attempted;
- no network-capable client is created;
- no credential lookup is performed;
- reports only include the disabled model disclosure.

## Explicit provider flags

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture locomo-mini \
  --run-id llm-judge-skip-demo \
  --output artifacts/benchmarks/llm_judge_skip_demo.json \
  --enable-answer-eval \
  --llm-judge-provider openai-compatible \
  --llm-judge-model <MODEL_NAME> \
  --llm-judge-api-key-env <ENV_NAME> \
  --llm-judge-output-jsonl artifacts/benchmarks/<RUN_ID>.llm_judge.jsonl
```

For local OpenAI-compatible endpoints:

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture locomo-mini \
  --run-id local-llm-judge-skip-demo \
  --output artifacts/benchmarks/local_llm_judge_skip_demo.json \
  --enable-answer-eval \
  --llm-judge-provider local-openai-compatible \
  --llm-judge-model <MODEL_NAME> \
  --llm-judge-base-url <LOCAL_OPENAI_COMPATIBLE_URL> \
  --llm-judge-api-key-env <ENV_NAME>
```

Raw API keys are not accepted as CLI values. Use an environment variable name or a key file path:

```text
--llm-judge-api-key-env OPENAI_API_KEY
--llm-judge-api-key-file /path/to/local/keyfile
```

The report records the environment variable name or that a key file was configured, but never serializes the key value.

## Skip-safe results

If an optional provider is requested but cannot run, backend metrics include:

```json
{
  "llm_judge": {
    "enabled": true,
    "status": "skipped",
    "skip_reason": "missing_api_key"
  }
}
```

Other skip reasons include:

- `missing_model`
- `missing_base_url`
- `missing_api_key`
- `missing_openai_dependency`
- `deterministic_answer_eval_required`
- `unsupported_provider`

A skip is not a benchmark failure. It records that supplementary judging did not run.

## Successful optional judging

When explicitly configured and available, optional judge rows include:

- provider and model disclosure;
- prompt template version;
- prompt template SHA-256;
- fixed temperature `0.0`;
- per-question verdict and score;
- deterministic verdict;
- deterministic-vs-LLM agreement;
- token usage when returned, otherwise estimates;
- cost estimate `unknown` unless pricing is explicitly configured in a future tranche.

Raw JSONL output is optional and must be under:

```text
artifacts/
reports/
tmp/
```

The JSONL path must end in `.jsonl`. Raw judge logs are private until reviewed.

## Claim rules

Allowed:

- The optional judge was disabled, skipped, or run under the recorded explicit configuration.
- Deterministic and optional judge agreement was X under the recorded run.
- Optional judge output is supplementary to deterministic answer evaluation.

Not allowed:

- promoting optional LLM judge results above deterministic metrics;
- treating skipped optional judging as a failed backend result;
- claiming full standard-dataset performance from fixture or bounded dry-run outputs;
- publishing raw judge JSONL without review;
- using credentials, paid APIs, or remote endpoints without explicit operator approval.

## Verification

P13-2 focused verification:

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_llm_judge.py
PYTHONPATH=.:src pytest -q tests/test_benchmark_phase13_runner_controls.py tests/test_benchmark_answerer_judge.py tests/test_benchmark_metrics.py
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

Full verification:

```bash
PYTHONPATH=.:src pytest -q
```
