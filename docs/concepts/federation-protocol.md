# Federation protocol

ShyftR multi-cell milestone federation is local-first and selective. It is not network synchronization, not hosted hosted platform behavior, and not a shortcut around regulator review.

## Package schema

A federation export package is JSON with these fields:

- `schema_version`: currently `federation.v1`.
- `export_id`: deterministic-looking local export identifier.
- `source_cell_id`: cell that produced the package.
- `source_cell_type`: metadata from the source manifest.
- `created_at`: export timestamp.
- `records`: selected approved records.
- `redaction_summary`: excluded/redacted counts and policy summary.
- `provenance`: export activity and derivation metadata.
- `policy_summary`: public-safe access policy summary.
- `package_signature`: reserved for a future signed package; currently `null`.

## Allowed record kinds

Exports may include only approved projections:

- approved memory;
- approved pattern;
- approved rule.

Exports exclude pending/rejected candidates, unreviewed imports, raw evidence by default, feedback/event logs, grid/index files, local absolute paths, secrets, and environment files.

## Import semantics

Import is review-gated:

1. A package is validated.
2. Selected records are written to `ledger/import_candidates.jsonl`.
3. `ledger/federation_events.jsonl` records the import event.
4. Imported records start with `imported` or `federated` trust labels.
5. Records are excluded from default packs/search until an explicit review approves them.
6. Approval writes `ledger/import_reviews.jsonl` and may create a verified local projection. Rejection keeps the audit trail and excludes the record from default packs.

## Trust labels

Allowed trust labels are:

- `local`: originated and approved in this cell;
- `imported`: received from another cell, not local truth;
- `federated`: received from an allowed federation source but still not local truth by default;
- `verified`: reviewed and approved for local use.

Authentication, if added later, must not become authorization. A signature can authenticate package origin; it cannot bypass import review by default.
