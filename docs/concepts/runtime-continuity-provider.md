# Runtime continuity provider

Status: implemented public alpha

Operator-facing alias: `carry`. The formal compatibility term remains `continuity`, but CLI, MCP, and HTTP surfaces should prefer `carry` for day-to-day use because it is shorter and less error-prone to type.

ShyftR can attach to two separate runtime needs:

- durable memory: reviewed facts and reusable lessons that should remain useful across sessions
- runtime continuity: bounded assistance around a context-compression event

The continuity provider does not replace a runtime's mechanical compactor. The runtime still decides how to trim, summarize, and protect recent context. ShyftR supplies a bounded continuity pack before compression and records feedback after resumed work.

## cells

A typical installation can use separate cells:

- memory cell: ordinary durable memory
- continuity cell: pack requests, continuity packs, carry-state checkpoints, feedback, synthetic evaluation reports, and review-gated promotion proposals
- live context cell: high-churn working context captured during a runtime session, then harvested or closed at session end

The continuity cell can read from the memory cell when configured by the operator. It should not directly mutate durable memory. Promotion notes from continuity feedback are written as proposals for review.

The live context cell is a separate implemented public-alpha role. It captures active session state without turning that state into durable memory by default. At session close, a harvest process classifies live context into discard, archive, continuity feedback, memory candidate, direct durable memory, or skill proposal buckets. The memory cell receives only policy-approved durable memory or review-gated proposals.

## relationship to live context optimization

Runtime continuity provider and live context optimization are complementary.

| Capability | Trigger | Primary cell | Output |
| --- | --- | --- | --- |
| continuity pack | context pressure or compaction event | continuity cell plus memory cell | bounded advisory pack |
| compaction feedback | after resumed work | continuity cell | useful, ignored, harmful, missing, or stale records |
| live context capture | during work | live context cell | working context entries |
| session harvest | session close | live context cell plus continuity cell | archive records, proposals, and durable memory candidates |

This keeps the prompt lean while allowing cells to preserve context evidence outside the active prompt. ShyftR should not be framed as increasing a model's hard context limit. The safer claim is that ShyftR helps runtimes reduce prompt bloat by capturing live working context and returning bounded relevant packs.

## modes

Supported modes:

- off: continuity is disabled and a disabled pack is returned
- shadow: ShyftR records what it would have selected, but exports no items to the runtime
- advisory: ShyftR returns bounded continuity items for the runtime compactor to use as scaffolding

Reserved mode:

- authority: reserved for a later operator-gated work slice

## command examples

Create cells:

```bash
shyftr init ~/.shyftr/cells/default-memory --cell-type memory
shyftr init ~/.shyftr/cells/default-continuity --cell-type continuity
```

Build an advisory carry pack:

```bash
shyftr carry pack \
  ~/.shyftr/cells/default-memory \
  ~/.shyftr/cells/default-continuity \
  "current task, operator decisions, safety constraints" \
  --runtime-id local-agent \
  --session-id session-001 \
  --compaction-id compaction-001 \
  --mode advisory \
  --max-items 8 \
  --max-tokens 1200 \
  --write
```

Record post-compression feedback:

```bash
shyftr carry feedback \
  ~/.shyftr/cells/default-continuity \
  continuity-pack-id \
  resumed_successfully \
  --runtime-id local-agent \
  --session-id session-001 \
  --compaction-id compaction-001 \
  --useful memory-example \
  --missing-note "adapter-specific resume hook was missing" \
  --promote-note "stable fact proposed for durable memory review" \
  --write
```

Run a deterministic synthetic evaluation:

```bash
shyftr carry eval \
  ~/.shyftr/cells/default-memory \
  ~/.shyftr/cells/default-continuity \
  "context compression continuity" \
  --expected-term continuity \
  --expected-term compression \
  --runtime-id synthetic-runtime \
  --task-id smoke-001 \
  --write
```

Inspect continuity ledgers:

```bash
shyftr carry status ~/.shyftr/cells/default-continuity
```

## mcp tools

The MCP bridge exposes carry tools plus continuity compatibility aliases:

- `shyftr_carry_pack`
- `shyftr_carry_feedback`
- `shyftr_carry_status`
- `shyftr_continuity_pack` compatibility alias
- `shyftr_continuity_feedback` compatibility alias
- `shyftr_continuity_status` compatibility alias

It also exposes live context optimization tools:

- `shyftr_live_context_capture`
- `shyftr_live_context_pack`
- `shyftr_live_context_checkpoint`
- `shyftr_live_context_resume`
- `shyftr_session_harvest`
- `shyftr_live_context_status`

Pack, feedback, capture, and harvest tools are dry-run by default unless `write=true` is supplied.

## local http service

The optional service exposes carry endpoints plus continuity compatibility endpoints:

- `POST /carry/pack`
- `POST /carry/feedback`
- `GET /carry/status`
- `POST /continuity/pack` compatibility endpoint
- `POST /continuity/feedback` compatibility endpoint
- `GET /continuity/status` compatibility endpoint

It also exposes live context optimization endpoints:

- `POST /live-context/capture`
- `POST /live-context/pack`
- `POST /live-context/checkpoint`
- `POST /live-context/resume`
- `POST /live-context/harvest`
- `GET /live-context/status`

The service delegates to the same continuity and live context modules as the CLI and MCP bridge.

## hardening posture

The alpha implementation enforces:

- explicit opt-in writes
- separate memory and continuity cell paths
- bounded max item and token settings
- shadow mode with no item export
- advisory mode with runtime-owned mechanical compression
- append-only continuity ledgers
- review-gated promotion proposals
- deterministic synthetic evaluation fixtures

## ledger files

The continuity cell seeds and writes:

- `ledger/continuity_events.jsonl`
- `ledger/continuity_packs.jsonl`
- `ledger/continuity_checkpoints.jsonl`
- `ledger/continuity_feedback.jsonl`
- `ledger/continuity_promotion_proposals.jsonl`
- `ledger/continuity_eval_reports.jsonl`


## carry-state behavior and phase 2 compatibility note

A continuity/carry pack can now merge two bounded inputs without changing its advisory posture:

- durable-memory retrieval from the memory cell;
- typed carry-state checkpoint material derived from the live context cell.

Carry-state items remain distinguishable in exported pack diagnostics and provenance so a runtime can inspect what came from current working state versus reviewed durable memory. When no carry-state exists, continuity behavior falls back to the previous durable-memory-only path.
