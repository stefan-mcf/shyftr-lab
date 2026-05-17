# P12-1: LongMemEval local mapping scaffold

Status: Phase 12 tranche P12-1 notes. This document does not claim a full LongMemEval benchmark run.

## Objective

Add a local-path, private-by-default mapping layer that converts a normalized LongMemEval-style JSON payload into the ShyftR benchmark fixture contract.

This tranche focuses only on:

- mapping and loading of a conservative normalized input shape;
- conversion helper script with guarded output paths and manifest sidecar;
- tests that enforce the privacy and output-safety rules.

No dataset downloads, no full LongMemEval runs, and no answer-eval in P12-1.

## Input contract (normalized)

Accepted minimal shape for a local input JSON file:

```json
{
  "dataset_version": "local-schema-smoke",
  "split": "longmemeval-standard-smoke",
  "contains_private_data": false,
  "cases": [
    {
      "question_id": "q-1",
      "question_type": "single-session-user",
      "question": "Where did the user put the blue notebook?",
      "answer": "on the kitchen shelf",
      "question_date": "2026-01-02",
      "haystack_session_ids": ["session-1"],
      "haystack_dates": ["2026-01-01"],
      "haystack_sessions": [
        [
          {"role": "user", "content": "I keep the blue notebook on the kitchen shelf.", "date": "2026-01-01"},
          {"role": "assistant", "content": "Noted.", "date": "2026-01-01"}
        ]
      ]
    }
  ]
}
```

Also accepted:

- a top-level list of case objects (treated as private-by-default for conversion).

## Privacy and safety gates

- `contains_private_data` defaults to true.
- The loader rejects `contains_private_data=true` unless `allow_private_data=True` is explicitly passed.
- The conversion helper refuses to write outside `artifacts/`, `reports/`, or `tmp/`.
- Conversion output must be a `.json` file.
- `--public-output` requires `contains_private_data=false` and refuses to write a private-marked fixture.

## Files

- `src/shyftr/benchmarks/longmemeval_standard.py`
  - `map_longmemeval_standard_payload(...)`
  - `load_longmemeval_standard_json(...)`
- `scripts/convert_longmemeval_standard_fixture.py`
  - `convert_longmemeval_standard_file(...)`
  - writes `.manifest.json` sidecar with input/output SHA-256 plus counts
- `tests/test_benchmark_longmemeval_standard_mapping.py`

## Claim limits

This tranche supports only:

- “ShyftR can map and convert a normalized local LongMemEval-shaped JSON into the fixture contract with privacy and output safety guards.”

This tranche does NOT support:

- “We ran LongMemEval.”
- Any performance comparisons or benchmark claims.

## P12-2 manifest addendum

The conversion sidecar now includes a nested LongMemEval case manifest with case/session/message counts, question-type counts, privacy posture, SHA-256 digests, and the per-question reset contract.
