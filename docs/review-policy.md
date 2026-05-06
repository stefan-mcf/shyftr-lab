# ShyftR review policy

ShyftR changes must preserve local-first operation, append-only ledger truth, provenance, and review gates. This policy applies to pull requests, local operator patches, and public proof artifacts.

## memory safety principles

Contributions that touch cell ledgers, regulator behavior, pack assembly, feedback, import/export, or memory promotion must preserve:

- append-only ledger truth: committed ledger records are not silently rewritten;
- provenance: memory records remain linked to the evidence and review activity that produced them;
- review gates: durable promotion, destructive deprecation, quarantine release, shared rules, and imported memory require explicit review;
- local defaults: tests and examples use synthetic or operator-approved data and avoid hidden hosted-service dependencies.

## regulator and policy changes

Changes to admission, privacy, retrieval, sensitivity, export, import, quarantine, or regulator logic must include:

- tests that exercise the changed policy path;
- a short description of what the change now allows, blocks, or labels;
- a note about pack, feedback, sensitivity, or export behavior when affected;
- confirmation that default examples still run locally without private data.

## schema and ledger format changes

Changes to SQLite schema, ledger record shape, JSONL event fields, or migration helpers must include migration notes in the pull request or closeout artifact:

- before and after shape;
- whether a migration step was added;
- whether existing local cells open without data loss;
- compatibility behavior for older ledgers when relevant.

Schema and ledger changes should add focused regression tests before broader tests are run.

## provenance-preserving memory writes

Every direct memory write path must preserve the provenance chain. Promotion, feedback recording, rule review, import review, federation, and evaluation metrics must not strip, rewrite, or fabricate provenance fields.

When a compatibility reader accepts older field names, the public-facing output should prefer current vocabulary such as `memory_id`, `cell`, `ledger`, `pack`, and `feedback`.

## required checks

Run the smallest relevant focused tests first, then the public gate bundle before merge or release-scope handoff:

```bash
python -m pytest -q
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

For release-scope or status changes, also run:

```bash
bash scripts/release_gate.sh
```

GitHub Actions should stay aligned with the local proof bundle where practical, while `scripts/release_gate.sh` remains the operator-local full bundle.

## review expectations

- Public docs and examples must avoid secrets, local absolute paths, private operator workflows, and real sensitive memory data.
- Public claims must match implemented and verified behavior.
- New compatibility behavior must be covered by tests and documented as compatibility, not primary vocabulary.
- A passing automated check does not replace operator review for gated memory-safety changes.
