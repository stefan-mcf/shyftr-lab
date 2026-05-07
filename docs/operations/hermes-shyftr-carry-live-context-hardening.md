# Hermes ShyftR carry/live-context hardening

This runbook verifies that a Hermes runtime can use ShyftR for context compaction support without giving ShyftR authority to mutate durable memory silently.

## Safety boundary

- `live_context` captures short-lived runtime entries and can harvest session closeout material.
- `carry` is the operator-facing alias for the formal `continuity` cell/provider surface.
- Carry/continuity packs are advisory context for the runtime compacter.
- Harvests may create review-gated memory or carry-improvement proposals.
- Direct durable-memory writes stay disabled unless an explicit runtime policy enables them.

## Cells

Default local Hermes deployment paths:

- memory: `~/.hermes/shyftr/cells/hermes-memory`
- carry/continuity: `~/.hermes/shyftr/cells/hermes-continuity`
- live context: `~/.hermes/shyftr/cells/hermes-live-context`

## One-shot smoke

From the repository root:

```bash
PYTHONPATH=src python scripts/shyftr_runtime_context_smoke.py
```

Expected result:

- `status` is `ok`
- `live_pack.items` is greater than zero
- `carry_pack.items` is greater than zero
- `harvest.review_gated` is `true`
- `harvest.direct_durable_memory_writes` is `0`
- `checks.approved_memory_ledger_unchanged_by_harvest` is `true`

Dry-run mode skips pack and harvest ledger writes. The smoke still writes synthetic setup live-context entries so the packer has public-safe material to retrieve:

```bash
PYTHONPATH=src python scripts/shyftr_runtime_context_smoke.py --dry-run
```

## Live runtime evaluator

Read-only health evaluation against the local Hermes cells:

```bash
PYTHONPATH=src python scripts/shyftr_context_quality_evaluator.py \
  --live-cell ~/.hermes/shyftr/cells/hermes-live-context \
  --carry-cell ~/.hermes/shyftr/cells/hermes-continuity \
  --min-entries 1 \
  --min-packs 1 \
  --min-harvests 1 \
  --min-carry-packs 1
```

The evaluator checks:

- live-context status is healthy;
- live-context remains advisory-only;
- carry/continuity status is healthy;
- carry promotions remain review-gated;
- minimum pack/harvest counts meet operator thresholds;
- harmful carry feedback rate, measured from `continuity_feedback.jsonl`, stays within the configured limit.

## Hermes runtime attachment check

The runtime compacter is considered attached when the active Hermes ShyftR plugin/config can do all of the following:

1. capture live-context entries before/during the session;
2. generate a live-context pack for compaction context;
3. generate a carry/continuity pack for compaction context;
4. harvest session-end or session-switch context with `write=true` when configured;
5. leave direct durable-memory write count at zero unless explicit policy allows it.

For already-running Hermes gateway/profile processes, restart or replace the process after plugin/config changes. Existing processes may retain the old plugin instance until restarted.

## Watchdog pattern

A local watchdog may run the evaluator with `--quiet-ok` on a schedule. It should stay silent on success and emit output only on failure so scheduler delivery remains low-noise.
