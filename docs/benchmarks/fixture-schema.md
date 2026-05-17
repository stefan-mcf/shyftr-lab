# Benchmark fixture schema

Status: Phase 11 planning surface. This schema defines the tiny public-safe fixture shape for the first benchmark harness.

## Purpose

The first benchmark fixture should be small, deterministic, and safe to commit. It exists to prove the adapter and report contracts before running larger datasets such as LOCOMO, LongMemEval, or BEAM.

## Top-level object

A fixture JSON object should include:

```json
{
  "schema_version": "shyftr-memory-benchmark-fixture/v0",
  "fixture_id": "synthetic-mini-001",
  "dataset_name": "synthetic-mini",
  "dataset_version": "v0",
  "contains_private_data": false,
  "conversations": [],
  "questions": []
}
```

Required fields:

- `schema_version`: fixed fixture schema identifier;
- `fixture_id`: stable fixture label;
- `dataset_name`: dataset label;
- `dataset_version`: fixture version;
- `contains_private_data`: must be false for committed fixtures;
- `conversations`: ordered conversation objects;
- `questions`: question objects for evaluation.

## Conversation object

A conversation object should include:

- `conversation_id`: stable id;
- `session_id`: optional session id;
- `started_at`: optional ISO-8601 timestamp;
- `messages`: ordered message objects;
- `metadata`: public-safe metadata.

A message object should include:

- `message_id`: stable id;
- `role`: `user`, `assistant`, `system`, or `tool`;
- `content`: public-safe text;
- `created_at`: optional ISO-8601 timestamp;
- `metadata`: public-safe metadata.

## Question object

A question object should include:

- `question_id`: stable id;
- `query`: text sent to backend search;
- `expected_answer`: optional answer text used only by evaluation;
- `expected_item_ids`: optional message or memory identifiers used only by evaluation;
- `question_type`: for example `factual`, `temporal`, `multi_hop`, or `preference`;
- `temporal_hint`: optional public-safe time hint;
- `evaluation_notes`: optional public-safe notes.

Expected answers and expected identifiers must never be provided to backend adapters during search. They are runner-only evaluation data.

## Minimal P11-1 fixture requirements

The first committed fixture should include:

- at least two conversations;
- at least four messages total;
- at least three questions;
- at least one factual recall question;
- at least one temporal or session-aware question;
- at least one question that the no-memory baseline should not answer from retrieved material.

## Larger dataset mapping

LOCOMO, LongMemEval, and BEAM adapters should map their native dataset rows into this fixture shape internally or emit an equivalent in-memory object. The repo should not vendor large datasets by default.
