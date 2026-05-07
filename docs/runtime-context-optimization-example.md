# Runtime context optimization example

This example shows a synthetic runtime-neutral flow for live context optimization. It does not use real transcripts, private runtime profile data, hosted services, or any default-on capture.

## flow

```text
create temporary cells
-> capture live context entries
-> request a bounded advisory pack
-> build a compact carry-state checkpoint
-> simulate context pressure and continuity feedback
-> reconstruct advisory resume state
-> close the session
-> harvest live context into review-gated outputs
-> inspect metrics and proposals
```

## fixture files

- `examples/integrations/runtime-context-optimization/live_context.jsonl` contains synthetic live context entries.
- `examples/integrations/runtime-context-optimization/session_closeout.json` contains a synthetic closeout summary and metrics.

## command sketch

```bash
shyftr init /tmp/shyftr-demo/live --cell-type live_context
shyftr init /tmp/shyftr-demo/continuity --cell-type continuity
shyftr init /tmp/shyftr-demo/memory --cell-type memory

shyftr live-context capture \
  /tmp/shyftr-demo/live \
  "Do not use real transcript fixtures or runtime profile data." \
  --runtime-id synthetic-runtime \
  --session-id demo-session \
  --task-id demo-task \
  --kind goal \
  --status active \
  --related-entry-id ops-proof \
  --confidence 0.9 \
  --evidence-ref docs/plan.md \
  --grounding-ref tests/test_cli_phase2_live_context.py \
  --retention-hint candidate \
  --sensitivity-hint public \
  --write

shyftr live-context pack \
  /tmp/shyftr-demo/live \
  "context optimization prompt budget verification" \
  --runtime-id synthetic-runtime \
  --session-id demo-session \
  --max-items 3 \
  --max-tokens 80 \
  --write

shyftr live-context checkpoint \
  /tmp/shyftr-demo/live \
  /tmp/shyftr-demo/continuity \
  --runtime-id synthetic-runtime \
  --session-id demo-session \
  --write

shyftr live-context resume \
  /tmp/shyftr-demo/continuity \
  --runtime-id synthetic-runtime \
  --session-id demo-session

shyftr carry pack \
  /tmp/shyftr-demo/memory \
  /tmp/shyftr-demo/continuity \
  "context optimization prompt budget verification" \
  --live-cell-path /tmp/shyftr-demo/live \
  --runtime-id synthetic-runtime \
  --session-id demo-session \
  --compaction-id demo-compaction \
  --mode advisory \
  --write

shyftr live-context harvest \
  /tmp/shyftr-demo/live \
  /tmp/shyftr-demo/continuity \
  /tmp/shyftr-demo/memory \
  --runtime-id synthetic-runtime \
  --session-id demo-session \
  --write

shyftr live-context metrics /tmp/shyftr-demo/live \
  --runtime-id synthetic-runtime \
  --session-id demo-session
```

## expected behavior

- Capture is append-only and content-hash deduped.
- External surfaces are dry-run unless `--write` or `write=true` is supplied.
- Packs are bounded by explicit item and token budgets.
- pack items are advisory and include provenance.
- Duplicate or already-present prompt content is suppressed.
- Session harvest writes review-gated proposals for durable memory candidates, continuity improvements, and skill proposals.
- Checkpoints and resume reconstructions remain advisory and compact; they do not mutate durable memory.
- Durable memory is not silently mutated.

## metrics

The synthetic demo records:

- pack item count;
- estimated pack tokens;
- duplicate suppression count;
- stale item suppression count;
- harvest bucket counts;
- memory proposal count;
- continuity improvement proposal count;
- carry-state checkpoint count and checkpoint token totals;
- useful, ignored, and harmful feedback rates when synthetic feedback rows exist;
- resume validation metrics such as missing-state and wrong-state counts when a resume flow is exercised.

## real-runtime gate

The real-runtime pilot remains operator-gated. Do not enable live capture in a real runtime profile, harvest private transcripts, change profile configuration, or claim hosted/package-release posture without explicit approval.
