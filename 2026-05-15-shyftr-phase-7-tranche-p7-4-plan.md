# ShyftR Phase 7 — Tranche P7-4 plan

Date: 2026-05-15
Repo: /Users/stefan/ShyftR
Phase: Phase 7 — privacy, policy, and safety hardening
Tranche: P7-4 — review surfaces and policy visibility
Status: in progress
Predecessor closeoff: `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-p7-3-closeoff.md`
Roadmap source: `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-tranche-p7-0-plan.md`

## Objective

Land the smallest additive review-surface improvement after P7-3 so policy-conflict and other challenger findings become operator-legible in read-only summaries and reports without introducing new ledgers, new authority, or automatic lifecycle mutation.

## Why this tranche is next

P7-3 made `policy_conflict` real inside Challenger reports, but that classification remained hard to inspect outside raw report JSON and raw ledger rows. The next highest-value gap is visibility, not stronger automation.

This tranche therefore focuses on:
- grouped audit visibility for challenger sparks;
- review-state visibility for sparks that have or have not been reviewed;
- hygiene/report surfacing of those audit findings;
- a CLI read surface that exposes the grouped summary without replacing the raw output path.

## Chosen minimal slice

1. Add `audit_summary(cell_path)` in `src/shyftr/audit.py`.
   - read-only helper;
   - groups challenger sparks by classification;
   - reports reviewed vs unreviewed state by linking audit reviews to spark identifiers;
   - returns deterministic summary payload plus per-finding visibility rows.

2. Extend `shyftr audit list` with `--summary`.
   - raw output remains the default;
   - `--summary` emits grouped review-surface visibility instead of raw spark/audit-row dumps.

3. Add `audit_findings` to `hygiene_report(...)`.
   - read-only report visibility only;
   - no new ledger writes;
   - no runtime-scope expansion.

4. Add focused RED tests first.
   - audit summary groups `policy_conflict` and contradiction findings;
   - audit summary distinguishes reviewed from unreviewed findings;
   - CLI help and CLI `audit list --summary` expose the grouped surface;
   - hygiene report includes audit visibility.

## Explicit stop boundary

This tranche does not include:
- automatic `mark_challenged` or isolation mutation from policy findings;
- new ledger files or schema migrations;
- dashboard/TUI/operator app work;
- broader contradiction arbitration beyond read-only visibility;
- final Phase 7 closeoff.

Those remain for P7-5 verification and final closeout only.

## Read-first files

- `src/shyftr/audit.py`
- `src/shyftr/audit/__init__.py`
- `src/shyftr/cli.py`
- `src/shyftr/reports/hygiene.py`
- `tests/test_audit.py`
- `tests/test_cli.py`
- `tests/test_hygiene.py`
- `tests/test_phase7_contradiction_safety.py`
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-p7-3-closeoff.md`

## Intended touchpoints

Core code:
- `src/shyftr/audit.py`
- `src/shyftr/audit/__init__.py`
- `src/shyftr/cli.py`
- `src/shyftr/reports/hygiene.py`

Focused tests:
- `tests/test_audit.py`
- `tests/test_cli.py`
- `tests/test_hygiene.py`
- `tests/test_phase7_contradiction_safety.py`

## RED tests for this tranche

1. audit summary groups `policy_conflict` and contradiction findings.
2. audit summary distinguishes reviewed vs unreviewed sparks.
3. `shyftr audit list --summary` emits grouped visibility payload.
4. hygiene report includes grouped audit visibility.

## Verification commands

Focused tranche verification:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_audit.py tests/test_cli.py tests/test_hygiene.py tests/test_phase7_contradiction_safety.py`

Broader follow-on verification for P7-5:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q`
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src python -m compileall -q src scripts examples`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-public-stale`
- `cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-capitalized-prose`
- `cd /Users/stefan/ShyftR && python scripts/public_readiness_check.py`
- `cd /Users/stefan/ShyftR && git diff --check`

## One-line summary

P7-4 should stop at a read-only audit-visibility layer that makes challenger policy outcomes and review state legible in summaries, CLI output, and hygiene reports without widening any authority surface.
