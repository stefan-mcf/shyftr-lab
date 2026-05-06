# ShyftR tranched plan status

Status: public-safe reconciliation snapshot for preparing the next larger phased run.

Plan reviewed:

- `docs/plans/2026-04-24-shyftr-implementation-tranches.md`

Current implementation truth:

- `docs/status/current-implementation-status.md`
- current public README and alpha gate
- latest green CI on `main`

## Summary

The public repo is ready for a larger run, but the next larger run should not start by adding distributed multi-cell features. The correct next run is a controlled Phase 8.5 public-alpha evidence run plus a reconciliation gate.

Current status:

| Area | Status | Evidence | Next action |
| --- | --- | --- | --- |
| Repository/CI | ready | clean `main`, public readiness PASS, latest CI green | keep exact-SHA gate before any larger run |
| Public alpha gate | ready | `scripts/alpha_gate.sh` reaches `ALPHA_GATE_READY` locally | require tester machines to run the same gate |
| Phase 0-2 core local loop | implemented/proven | current status matrix, tests, local lifecycle, console build | regression guard only |
| Phase 3 runtime/pilot harness | partial | runtime-neutral examples and synthetic fixtures exist | prove at least one real or replayable pilot loop before closing 8.5 |
| Phase 4-5 local advisory/durability surfaces | implemented enough for alpha claims | sweep/challenge/quarantine, backup/restore, ledger verification, privacy/sensitivity tests | keep as regression guards during alpha |
| Phase 6 distributed multi-cell intelligence | not implemented | current status matrix says no current surface | do not start without a separate approval and plan |
| Phase 7 private-core-adjacent differentiators | not public-run ready | advanced confidence/ranking/compaction can be moat-bearing | route private-core experiments first when needed |
| Phase 8 productization | active | README, docs, alpha gate, CI are public-ready | continue at Tranche 8.5 |

## Current larger-run start point

Start from:

- `Tranche 8.5: Public Alpha`

Do not start from:

- Phase 6 multi-cell work;
- Phase 7 advanced confidence/ranking/simulation work;
- Checkpoint E alpha-exit;
- Checkpoint F stable-release language cleanup.

## Why Tranche 8.5 is the right next run

Tranche 8.5 is the first tranche whose remaining evidence cannot be proven solely by local tests. The codebase now has enough alpha infrastructure to invite technical testers, but the tranche itself still needs external proof:

- 3-5 external technical testers can run clone/install/gate/demo;
- failures become actionable issues;
- the product value is understandable without live explanation;
- at least one real or replayable runtime/pilot loop is proven or explicitly scoped out for the first alpha wave.

## Required larger-run waves

### Wave 0: preflight and freeze

Gate type: pre-flight.

Objective: confirm the exact public SHA is healthy before sending anyone instructions.

Commands:

```bash
git fetch origin main
git status --short --branch
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
python scripts/public_readiness_check.py
bash scripts/alpha_gate.sh
```

Pass condition:

- worktree clean;
- local HEAD equals `origin/main`;
- public readiness PASS;
- alpha gate ends with `ALPHA_GATE_READY`;
- GitHub CI is green for the exact SHA.

Failure behavior:

- block tester outreach;
- repair the failing gate;
- rerun Wave 0.

### Wave 1: alpha tester packet

Gate type: pre-flight.

Objective: prepare tester instructions without changing the approved public README.

Artifact:

- `docs/status/alpha-readiness.md` remains the canonical tester limits document.
- A short private/outbound message can link the public README and tell testers to run `bash scripts/alpha_gate.sh`.

Tester scope:

- clone/install;
- run alpha gate;
- run deterministic lifecycle example;
- optionally inspect the local console;
- report confusing docs, install issues, gate failures, and concept clarity.

Do not ask testers to use private, customer, employer, regulated, or production memory.

### Wave 2: runtime/pilot proof lane

Gate type: revision.

Objective: satisfy or explicitly narrow Tranche 8.5 requirement 7.

Preferred public-safe option:

- run the existing runtime-neutral file/JSONL adapter example as a replayable pilot harness;
- capture evidence that the loop moves from evidence to candidate to memory to pack to feedback;
- record diagnostics/readiness evidence in `docs/status/` without private paths or real data.

If a true real-runtime loop is not ready:

- keep Tranche 8.5 marked partial;
- state that this alpha wave is clone/install/synthetic-demo validation only;
- do not claim the tranche is complete.

Private-core route:

- if the pilot lane needs private scoring/ranking/compaction, route that experiment to `shyftr-private-core` and publish only public contracts or synthetic fixtures here.

### Wave 3: external tester evidence

Gate type: revision.

Objective: collect enough feedback to decide whether Tranche 8.5 can use externally validated alpha language.

Minimum evidence when external validation is claimed:

- tester count;
- exact SHA tested;
- OS/Python/Node versions;
- alpha gate verdict;
- install friction;
- demo/lifecycle success or failure;
- first-impression concept clarity;
- actionable bug list.

Rescope behavior:

- if fewer than 3 technical testers complete the gate, do not claim external alpha validation;
- the operator may explicitly defer this evidence and continue pre-Phase-6 planning from local gates and operator usability acceptance;
- keep the external evidence tracker open and record reports when they arrive.

### Wave 4: Tranche 8.5 closeout decision

Gate type: escalation.

Objective: decide whether to close Tranche 8.5, keep it open, or split remaining proof into a follow-up tracker.

Close only as externally validated if:

- CI and local gates remain green;
- tester evidence is recorded;
- runtime/pilot proof is satisfied or explicitly scoped out for the first alpha wave;
- product value is understandable enough from public docs and tester reports.

If not externally validated:

- split or keep the tester-evidence track open;
- allow continued pre-Phase-6 planning only if explicitly operator-rescoped from local gate evidence;
- do not proceed to Checkpoint E or stable-release language from local-only evidence.

## Private-core separation during the run

Before each wave, apply PC-0 from the private overlay:

- public proof, public contract, and public synthetic examples stay in this repo;
- private scoring, ranking, compaction, commercial strategy, and real pilot data stay private;
- public status docs must not expose private runtime/operator details.

## Larger-run worker shape

Recommended shape: phased-assembly with twin-inspection overlay.

Suggested lane split:

| Lane | Scope | Owner shape | Notes |
| --- | --- | --- | --- |
| controller/integration | exact SHA, final docs, commits, CI | controller | one mutating owner for canonical repo |
| gate runner | public readiness, alpha gate, CI watch | bounded helper or controller | no code changes unless assigned |
| docs/status lane | tester packet and status evidence | bounded helper | public-safe wording only |
| runtime proof lane | replayable adapter/pilot evidence | bounded helper or isolated branch | no private data |
| review lane | spec/quality/readiness review | independent reviewer | read-only unless routed back |

Persistent swarm profiles are not required unless the run becomes long-lived or multi-day. Use them only with explicit profile assignments and file-backed artifacts.

## Ready-to-run verdict

Ready for larger phased run: yes, with the run starting at Tranche 8.5 and Wave 0.

Not ready for: Checkpoint E, Checkpoint F, Phase 6, or private-core-heavy Phase 7 work.
