# P11-4d: LOCOMO-standard mapping layer

Status: download-free scaffold for future standard-dataset runs.

This tranche adds a local mapping layer for normalized LOCOMO-style JSON input. It does not download, vendor, or run the full LOCOMO dataset.

## What is supported

A local JSON file can be mapped into the Phase 11 `BenchmarkFixture` contract with:

```bash
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture locomo-standard \
  --fixture-path /path/to/local/locomo-standard.json \
  --fixture-format locomo-standard \
  --allow-private-fixture \
  --run-id locomo-standard-local \
  --output artifacts/benchmarks/locomo_standard_local.json \
  --top-k 1,3,5 \
  --timeout-seconds 60 \
  --max-retries 1
```

The `--allow-private-fixture` flag is intentionally explicit. Native LOCOMO-style input is treated as private unless the local JSON declares `contains_private_data: false`.

## Expected normalized input shape

The mapper accepts a conservative normalized shape:

```json
{
  "dataset_version": "local-schema-smoke",
  "split": "locomo-standard-smoke",
  "contains_private_data": false,
  "conversations": [
    {
      "session_id": "session-1",
      "started_at": "2026-01-01T00:00:00Z",
      "messages": [
        {
          "turn_id": "turn-1",
          "speaker": "user",
          "text": "Example public-safe message.",
          "timestamp": "2026-01-01T00:01:00Z"
        }
      ]
    }
  ],
  "questions": [
    {
      "qa_id": "qa-1",
      "question": "Example question?",
      "answer": "Example answer",
      "evidence_message_ids": ["turn-1"],
      "category": "single-hop",
      "session_id": "session-1"
    }
  ]
}
```

Accepted aliases are intentionally small and documented in code:

- conversations: `conversations`, `sessions`, or `dialogues`
- messages: `messages`, `turns`, or `dialogue`
- message id: `message_id`, `turn_id`, or `id`
- message text: `content`, `text`, `utterance`, or `message`
- questions: `questions`, `qa`, or `qas`
- expected item ids: `expected_item_ids`, `evidence_message_ids`, or `answer_message_ids`

## Claim boundaries

Allowed:

- ShyftR can map a local normalized LOCOMO-style JSON file into the fixture contract.
- The runner can execute the mapped fixture with the existing adapter harness.

Not allowed:

- This is a full LOCOMO run.
- This proves task-success lift or superiority.
- This validates LongMemEval or BEAM.
- This relaxes review, provenance, or privacy gates.
