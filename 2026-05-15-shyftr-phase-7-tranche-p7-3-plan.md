# ShyftR Phase 7 — Tranche P7-3 plan (contradiction + poisoning/prompt-injection fixtures)

Date: 2026-05-15
Repo: /Users/stefan/ShyftR
Phase: Phase 7 — privacy, policy, and safety hardening
Tranche: P7-3 (smallest additive slice)
Status: in progress
Predecessor closeoff: `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-p7-2-closeoff.md`

## Objective

Land the smallest fixture-safe, local-first safety slice after P7-2 by adding deterministic contradiction/poisoning/prompt-injection fixtures and a minimal contract in the Challenger.

This tranche is intentionally conservative:
- it does not mutate lifecycle state
- it only emits classifications via dry-run Challenger reports (and optionally audit sparks when explicitly enabled)
- it stays local-first and append-only

## Smallest P7-3 slice chosen

Add a minimal **policy_conflict** classification path in the Challenger driven by fixture-safe spark text markers that resemble prompt-injection or policy-violating instructions.

Why this is the smallest honest advance after P7-2:
- P7-2 tightened privacy redaction across pack/export surfaces.
- The next tranche target is contradiction/poisoning fixtures.
- The Challenger already has a reserved `policy_conflict` classification but no behavior behind it.
- Adding a conservative, deterministic heuristic for `policy_conflict` is additive, local-first, and gives the repo a stable fixture surface to extend later.

## Behavioral contract (P7-3)

1) If `ledger/sparks.jsonl` contains a spark linked to an approved-memory record whose `text` includes prompt-injection-like policy markers (case-insensitive), the Challenger MUST emit a finding with:
- `classification == "policy_conflict"`
- `supporting_data.policy_signal == "prompt_injection_like"`

2) Existing behavior remains intact:
- Harmful outcomes continue to produce `direct_contradiction` findings.
- No lifecycle ledgers are mutated by Challenger runs.

## Implementation touchpoints

- `src/shyftr/audit/challenger.py`
  - classify certain spark text as evidence direction `policy`
  - convert `policy` evidence into a `policy_conflict` ChallengerFinding

- `tests/test_phase7_contradiction_safety.py`
  - new fixture-safe tests proving:
    - prompt-injection-like spark text produces `policy_conflict`
    - harmful outcome flags still produce `direct_contradiction`

## Verification commands (focused)

RED/GREEN loop:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_phase7_contradiction_safety.py`

Focused tranche regression after GREEN:
- `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q tests/test_phase7_contradiction_safety.py tests/test_memory_evolution_supersession.py tests/test_sweep.py tests/test_memory_provider.py`

## Stop boundary

This tranche stops once:
- the fixture-safe tests exist and are green
- the Challenger emits `policy_conflict` only as a report classification (and only writes sparks when explicitly enabled)
- no other policy machinery, durable write authority changes, or hosted integrations are introduced
