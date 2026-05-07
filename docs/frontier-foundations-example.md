# Frontier public-safe example

This example uses synthetic data only. It demonstrates the implemented frontier local local-reviewed surfaces without private memory data or private-core algorithms.

## 1. Create a local cell

```bash
python -m shyftr.cli init /tmp/shyftr-frontier-demo --cell-id frontier-demo
```

## 2. Add synthetic reviewed memory

Append or ingest ordinary public-safe fixtures, then promote reviewed memory through the normal review path. For direct development tests, synthetic rows can include scalar confidence plus counters:

```json
{"memory_id":"m-deploy-1","cell_id":"frontier-demo","statement":"Run deterministic tests before changing retrieval policy.","confidence":0.9,"success_count":3,"failure_count":0,"kind":"workflow","status":"approved"}
```

Pack projection keeps scalar `confidence` and adds display metadata for expected confidence and uncertainty.

## 3. Compare retrieval modes read-only

```bash
python -m shyftr.cli simulate /tmp/shyftr-frontier-demo "retrieval policy" --current-mode balanced --proposed-mode conservative
```

The report shows selected IDs, missed IDs, caution labels, and estimated token usage. It does not apply settings.

## 4. Inspect graph and reputation surfaces

```bash
python -m shyftr.cli graph /tmp/shyftr-frontier-demo
python -m shyftr.cli reputation /tmp/shyftr-frontier-demo
python -m shyftr.cli regulator-proposals /tmp/shyftr-frontier-demo
```

These are review-oriented projections. Graph edges require provenance and reviewer metadata. Reputation is advisory. regulator proposals require human review and a simulation reference before any future policy change.

## 5. Generate synthetic eval tasks

```bash
python -m shyftr.cli evalgen /tmp/shyftr-frontier-demo --output /tmp/shyftr-frontier-evals.json
```

Eval tasks are deterministic and provenance-linked. They are intended for regression checks using synthetic or operator-approved data only.

## Public safety notes

- Do not use real private memory in public fixtures.
- Do not treat reputation as permission to bypass review.
- Do not auto-apply policy changes from simulation.
