# ShyftR Phase 10 local evaluation demo

This demo shows a public-safe, local-only closeout-to-memory-to-pack flow with
Phase 10 evaluation surfaces. It uses synthetic evidence and append-only cell
ledgers. It does not require a hosted service, production account, external
judge, package release, or private scoring logic.

## What the demo proves

- A closeout file can be ingested as evidence.
- A candidate can be reviewed and promoted to memory.
- A pack can be assembled from local memory.
- feedback can record useful and missed memory ids.
- `shyftr metrics` reports deterministic effectiveness proxies from usage and
  feedback ledgers.
- `shyftr decay` reports transparent decay scoring plus review-gated
  deprecation proposal counts.

## Example commands

Run from the repository root with `PYTHONPATH=src`:

```bash
CELL=/tmp/shyftr-phase10-demo-cell
rm -rf "$CELL"
PYTHONPATH=src python -m shyftr.cli init-cell "$CELL" --cell-id phase10-demo --cell-type domain
PYTHONPATH=src python -m shyftr.cli ingest "$CELL" examples/closeout.md --kind closeout
```

Use the returned `evidence_id` to extract a candidate:

```bash
PYTHONPATH=src python -m shyftr.cli candidate "$CELL" <evidence_id>
```

Use the returned `candidate_id` to approve and promote it:

```bash
PYTHONPATH=src python -m shyftr.cli approve "$CELL" <candidate_id> \
  --reviewer operator \
  --rationale "Synthetic demo lesson is safe and useful"

PYTHONPATH=src python -m shyftr.cli promote "$CELL" <candidate_id> \
  --promoter operator \
  --statement "feedback-derived local metrics show whether retrieved memories helped future packs."
```

Assemble a pack and record feedback:

```bash
PYTHONPATH=src python -m shyftr.cli pack "$CELL" "evaluate memory pack usefulness" --task-id phase10-demo-task

PYTHONPATH=src python -m shyftr.cli feedback "$CELL" <pack_id> success \
  --applied <memory_id> \
  --useful <memory_id> \
  --verification '{"demo":"phase10-local"}'
```

Inspect Phase 10 proof surfaces:

```bash
PYTHONPATH=src python -m shyftr.cli metrics "$CELL"
PYTHONPATH=src python -m shyftr.cli decay "$CELL"
```

## Scope boundary

The metrics are local release evidence. They are not alpha-exit,
stable-release, hosted-service, production, or package-release claims.
