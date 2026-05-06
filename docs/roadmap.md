# ShyftR roadmap

Status: public roadmap for local-first alpha planning.

## Current alpha surface

ShyftR proves local-first memory cells, append-only ledger truth, review-gated memory promotion, pack generation, feedback recording, local service/console operation, adapter discovery, and public-safe runtime integration examples.

## Phase 8 productization sequence

1. Product docs and guides.
2. Adapter SDK guide, template, and harness.
3. `/v1` local HTTP API namespace and OpenAPI contract.
4. Public alpha evidence collection.
5. Desktop shell only after operator review justifies packaging work.

## Phase 9 integration adapter sequence

1. Generic evidence adapters using the existing `SourceAdapter` protocol.
2. Closeout artifact adapter for public-safe task/domain handoffs.
3. Generic adapter ingestion into local evidence ledgers.
4. Retrieval usage log contract for local generic clients.
5. Operator gate before Phase 10.

Status record: `docs/status/phase-9-integration-adapters-closeout.md`.

## Operator release-scope gate

Before alpha-exit or stable-release wording, ShyftR needs a separate operator gate with exact-SHA CI, local verification, release-scope review, and documented acceptance.

## Out of scope for public alpha

Hosted SaaS, production multi-tenancy, real customer data, private-core scoring/ranking/compaction, and removal of alpha posture remain out of scope until later explicit gates pass.
