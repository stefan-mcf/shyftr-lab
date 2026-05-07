# local evaluation track closeout evidence sample

Kind: closeout

## Durable Lesson

When a pack is used for a task, feedback should record which memories were
useful, which memories were missed, and what evidence supported that judgment.
Local evaluation can then compute deterministic effectiveness metrics without
an external evaluator.

## Verification Evidence

- The pack was generated from approved local memory.
- feedback was recorded through the append-only ledger.
- Metrics and decay reports are read-only projections.

## Reuse Guidance

Use `shyftr metrics <cell_path>` after recording feedback to inspect retrieval
quality, successful reuse, failed reuse, confidence adjustment proposals, and
review-gated decay scoring.
