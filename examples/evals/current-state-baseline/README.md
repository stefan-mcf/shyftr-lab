# Current-state baseline

This directory holds the synthetic, repo-local baseline harness for current ShyftR memory behavior.

## Scope

The harness measures current public-safe behavior only:
- Mode A: durable-memory-only;
- Mode B: durable + carry/continuity;
- Mode C: durable + carry/continuity + live-context;
- Mode D: current pack/loadout behavior capture and normalization.

## Non-goals

This harness does not:
- implement typed working memory;
- redesign retrieval;
- broaden ShyftR into a heavy benchmark suite;
- use real user transcripts, private runtime profiles, customer data, employer data, or regulated data;
- claim hosted, multi-tenant, or market-superiority results.

## Evidence boundary

All fixtures are synthetic. All writes go to temp cells created during the run. The harness never writes to non-temp user cells.

## Local commands

Single fixture, one mode:

```bash
python scripts/current_state_baseline.py --fixture preference-recall --mode durable
```

All fixtures, one mode:

```bash
python scripts/current_state_baseline.py --mode carry
```

Full baseline:

```bash
python scripts/current_state_baseline.py --mode all
```

Compare two summaries:

```bash
python scripts/compare_current_state_baseline.py \
  docs/status/current-state-baseline-summary.json \
  docs/status/current-state-baseline-summary.json
```

## Output artifacts

Primary outputs:
- `docs/status/current-state-baseline-report.md`
- `docs/status/current-state-baseline-summary.json`
- `docs/status/current-state-baseline-closeout.md`
- per-mode docs under `docs/status/`

Fixtures and contracts:
- `fixtures/*.json`
- `expected/*.json`
- `metrics-contract.md`

## How later work should use this

Before judging schema/model unification, typed live-context evolution, retrieval redesign, or memory-class expansion complete, rerun this harness and compare the new summary JSON against the current baseline.

Suggested comparison command:

```bash
python scripts/compare_current_state_baseline.py \
  docs/status/current-state-baseline-summary.json \
  path/to/candidate-summary.json \
  --markdown-out docs/status/current-state-baseline-comparison.md
```
