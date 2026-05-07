# Autonomous memory evolution

ShyftR regulated autonomous memory evolution is a public-safe proposal layer over append-only cell ledgers.

Autonomous means detect and propose by default. It does not mean silent mutation.

## What the scanner can propose

- split an oversized or multi-topic candidate before promotion;
- merge duplicate or overlapping memory records while preserving provenance lineage;
- supersede, replace, deprecate, forget, or redact memory after repeated feedback or explicit policy evidence. In the public baseline, accepting `supersede_memory` uses the same append-only lifecycle exclusion path as `deprecate_memory`; richer graph-edge/new-memory supersession remains review/operator controlled;
- promote a missing memory from feedback when a future public-safe detector emits that proposal type. regulated autonomous memory evolution track can represent and simulate this proposal type, but accepting it is explicitly unimplemented rather than silently no-oping;

## What never happens silently

- historical ledger rows are not rewritten;
- child candidates are not auto-promoted after a split;
- duplicate memories are not merged without review;
- forget/redact/deprecate are logical lifecycle events, not normal physical deletion;
- retrieval-affecting proposals require simulation before acceptance.

## Operator flow

```bash
shyftr evolve scan <cell_path> --dry-run
shyftr evolve scan <cell_path> --write-proposals
shyftr evolve proposals <cell_path>
shyftr evolve simulate <cell_path> <proposal_id> --append-report
shyftr evolve review <cell_path> <proposal_id> --decision defer --rationale "needs operator review"
```

Use `accept` only after checking the proposal rationale, evidence refs, projection delta, and simulation output. Accepted proposals go through existing review or lifecycle event paths and remain append-only.

## Public/private split

The public implementation uses deterministic heuristics and synthetic fixtures. Private scoring, private embeddings, real-data calibration, legal retention automation, hosted scheduling, and production compliance authority remain outside public `main` unless explicitly approved later.
