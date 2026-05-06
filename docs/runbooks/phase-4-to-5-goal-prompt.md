# `/goal` Prompt: Phase 4 to Phase 5 Durability Checkpoint

Use this from the repository root after the repo is clean and the Phase 2/3 console checkpoint is present.

```text
Proceed optimally with ShyftR from Tranche 4.1 through the Phase 5 durability checkpoint.

Source of truth:
- docs/plans/2026-04-24-shyftr-implementation-tranches.md
- Start at: Phase 4 / Tranche 4.1 Sweep Proposal Engine
- Stop at: Phase 5 Gate: Durability Checkpoint
- Do not start Phase 6 without a new instruction.

Execution rules:
- Follow every tranche gate exactly before committing that tranche.
- Use tranche-sized commits with the commit messages specified in the plan where possible.
- Preserve ShyftR rule: cell ledgers are canonical truth; grid/API/UI/Sweep/Challenger are projections or delegated append-only writers only.
- Treat active-learning outputs as review-gated proposals, audit candidates, lifecycle events, or projections until explicit review applies authority.
- Deduplicate proposals against decision-folded open proposal projections, not raw proposal rows.
- Do not silently mutate memory confidence, lifecycle, retrieval affinity, pack output, text, scope, or provenance.
- Stop early only for failing tests that cannot be resolved, dependency/auth failure, unclear destructive migration risk, a violated cell-ledger authority boundary, or a reviewer gate that returns blocking issues.

Required sequence:
1. Tranche 4.1: Sweep Proposal Engine
2. Tranche 4.1G: Proposal Review Regression Gate
3. Tranche 4.2: Challenger Audit Loop
4. Tranche 4.3: quarantine and Challenge Workflow
5. Tranche 4.4: memory Conflict Arbitration
6. Phase 4 Gate: Active-Learning Authority Review
7. Tranche 5.1: grid Metadata and Staleness
8. Tranche 5.3: Backup and Restore
9. Tranche 5.4: Tamper-Evident Ledger Hash Chains
10. Tranche 5.5: Privacy and Sensitivity Scoping
11. Tranche 5.2: Disk-Backed Vector Adapter only if optional dependency risk remains bounded; otherwise document deferral and continue to the Phase 5 Gate.
12. Phase 5 Gate: Durability Checkpoint, then stop and report.

Closeout must include:
- final commit SHA(s);
- tests and exact results;
- reviewer verdict;
- any deferred 5.2 rationale;
- explicit confirmation that Phase 6 was not started.
```
