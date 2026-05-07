# Multi-cell example

This public-safe example demonstrates multi-cell milestone behavior with synthetic cells only.

## Scenario

- `project-alpha` has an approved local memory: retry API requests with bounded backoff.
- `project-beta` has a similar approved local memory.
- A registry tracks both cells as metadata-only entries.
- A dry-run resonance scan over explicitly selected cells finds the repeated memory.
- A shared rule proposal is created, but it is not approved automatically.
- The operator approves a scoped rule.
- A pack for the allowed scope can include the approved rule.
- A selective export/import round trip starts with imported trust and requires review before use.

## CLI outline

```bash
python -m shyftr.cli init examples/multi-cell/project-alpha --cell-id project-alpha
python -m shyftr.cli init examples/multi-cell/project-beta --cell-id project-beta
python -m shyftr.cli cell register --registry examples/multi-cell/registry.jsonl --cell-id project-alpha --cell-type project --path examples/multi-cell/project-alpha --owner operator --domain demo --trust-boundary local --tags synthetic
python -m shyftr.cli cell register --registry examples/multi-cell/registry.jsonl --cell-id project-beta --cell-type project --path examples/multi-cell/project-beta --owner operator --domain demo --trust-boundary local --tags synthetic
python -m shyftr.cli resonance scan --registry examples/multi-cell/registry.jsonl --cell project-alpha --cell project-beta --dry-run
```

The public-safe demonstration creates temporary synthetic cells and documents registry-scoped resonance, review-gated shared rules, selective export, imported trust labels, and review before pack inclusion.

## Safety notes

Default pack/search behavior remains single-cell. Cross-cell behavior requires explicit registry and cell selection. Imported or federated records are not local truth until reviewed. frontier foundations track behavior is not part of this example.
