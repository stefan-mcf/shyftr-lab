# Public alpha wave 0-4 evidence

Status: Wave 0-4 execution record for Tranche 8.5 public alpha.

Recorded: 2026-05-06T08:09:52Z

Wave 0 preflight public SHA: `c610174c037d9bf7999bc4d747488cada84d6df9`

Wave 0 preflight CI evidence:

- Workflow: CI
- Run: https://github.com/stefan-mcf/shyftr/actions/runs/25423497127
- Conclusion: success

## Scope and stop limit

This run starts from Tranche 8.5 public alpha and stops before any distributed multi-cell intelligence work. It does not begin Phase 6, Checkpoint E, Checkpoint F, or private-core-heavy work.

Public/private split for this run:

- Public proof, public contracts, and public synthetic examples stay in this repo.
- Real private runtime data, private scoring/ranking/compaction experiments, and commercial strategy stay outside this repo.
- Tester evidence recorded here must be public-safe and must not include secrets, private local paths, customer data, employer data, regulated data, or production memory.

## Wave 0: preflight and freeze

Gate type: pre-flight.

Result: PASS after fast-forwarding local `main` to `origin/main`.

Commands verified:

```bash
git fetch origin main
git status --short --branch
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
python scripts/public_readiness_check.py
bash scripts/alpha_gate.sh
gh run list --repo stefan-mcf/shyftr --commit c610174c037d9bf7999bc4d747488cada84d6df9 --limit 10
```

Evidence:

- worktree status: `## main...origin/main`
- local HEAD: `c610174c037d9bf7999bc4d747488cada84d6df9`
- `origin/main`: `c610174c037d9bf7999bc4d747488cada84d6df9`
- public readiness: `PASS`
- alpha gate final verdict: `ALPHA_GATE_READY`
- alpha gate test suite: `758 passed, 1 warning`
- console build: passed
- dependency audit: `found 0 vulnerabilities`
- exact-SHA CI: success

Notes:

- Initial Wave 0 preflight found local `main` one commit behind `origin/main`; it was repaired with a fast-forward pull before rerunning the gate.
- The fast-forward changed `docs/example-lifecycle.md` only.

## Wave 1: alpha tester packet

Gate type: pre-flight.

Result: READY.

Canonical tester limits document remains:

- `docs/status/alpha-readiness.md`

Tester scope for outbound use:

- clone the public repo;
- install from clone using README instructions;
- run `bash scripts/alpha_gate.sh`;
- run or inspect the deterministic lifecycle example;
- optionally inspect the local console;
- report confusing docs, install issues, gate failures, demo failures, and concept-clarity feedback.

Outbound message draft:

```text
ShyftR is ready for a small local-first alpha check by technical testers.

Please use the public README, clone the repo, install from clone, and run:

bash scripts/alpha_gate.sh

Expected final line:

ALPHA_GATE_READY

Use synthetic or intentionally non-sensitive test data only. Do not use customer, employer, regulated, confidential, production memory, API keys, tokens, private keys, or .env files.

Please report:
- OS and version;
- Python version;
- Node/npm version if the console build runs;
- whether the alpha gate reached ALPHA_GATE_READY;
- the full error output if it failed;
- which README/docs step was confusing;
- whether the lifecycle demo made the pack -> feedback loop understandable;
- anything that would block a small local pilot.
```

## Wave 2: runtime/pilot proof lane

Gate type: revision.

Result: REPLAYABLE PUBLIC-SAFE PILOT PROOF PASSED.

Public-safe route selected:

- Existing runtime-neutral file/JSONL adapter example.
- Synthetic fixture path: `examples/integrations/worker-runtime/`
- Demo doc: `docs/runtime-integration-example.md`
- End-to-end proof test: `tests/test_runtime_integration_demo.py`

Commands verified:

```bash
python -m pytest -q tests/test_runtime_integration_demo.py
PYTHONPATH=src python -m shyftr.cli adapter validate --config examples/integrations/worker-runtime/adapter.yaml
PYTHONPATH=src python -m shyftr.cli adapter discover --config examples/integrations/worker-runtime/adapter.yaml --dry-run
PYTHONPATH=src python -m shyftr.cli init "$cell"
PYTHONPATH=src python -m shyftr.cli adapter ingest --config examples/integrations/worker-runtime/adapter.yaml --cell-path "$cell"
```

Evidence:

- focused runtime integration test: `3 passed`
- adapter validation status: `ok`
- discovery dry-run: `total_sources=5`, `inputs_processed=4`, `errors=[]`
- ingest status: `ok`, `sources_ingested=5`, `sources_skipped=0`, `errors=[]`
- demo test proves the closed loop from runtime evidence through candidate extraction, review, memory promotion, pack request, and feedback acceptance.

Decision:

- Requirement 7 is satisfied for the first alpha wave as a replayable public-safe pilot harness.
- A true real-runtime loop remains a later/operator-owned evidence item and must not be claimed from this synthetic run.

## Wave 3: external tester evidence

Gate type: revision.

Result: NOT ENOUGH EXTERNAL TESTER EVIDENCE TO CLOSE TRANCHE 8.5.

Evidence collected during this run:

| Field | Current value |
| --- | --- |
| tester count | 0 external testers completed during this local run |
| pre-template tested SHA | `c610174c037d9bf7999bc4d747488cada84d6df9` |
| local alpha gate verdict | `ALPHA_GATE_READY` |
| external alpha gate verdicts | none yet |
| install friction | none from external testers yet |
| demo/lifecycle result | local gate passed; external results pending |
| concept clarity | external results pending |
| actionable bug list | none from external testers yet |

Stop-condition application:

- Fewer than 3 technical testers completed the gate, so Tranche 8.5 remains open.
- Tester outreach may proceed using the Wave 1 packet, but closure requires returned external evidence.

External tester evidence rows to add when available:

| Tester label | SHA | OS | Python | Node/npm | Alpha gate verdict | Install friction | Demo/lifecycle result | Concept clarity | Bugs/issues |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pending | record tester's `git rev-parse HEAD` | pending | pending | pending | pending | pending | pending | pending | pending |

## Wave 4: Tranche 8.5 closeout decision

Gate type: escalation.

Decision: KEEP TRANCHE 8.5 OPEN.

Closeout checks:

| Requirement | Status | Evidence |
| --- | --- | --- |
| CI and local gates remain green | pass | exact-SHA CI success, public readiness PASS, alpha gate `ALPHA_GATE_READY` |
| tester evidence is recorded | partial | local evidence recorded; 0 external testers completed |
| runtime/pilot proof satisfied or narrowed | pass for first alpha wave | replayable runtime-neutral adapter harness passed |
| product value understandable from public docs and tester reports | partial | public docs ready; tester reports pending |

Result:

- Tranche 8.5 cannot close yet because external tester evidence is missing.
- No Checkpoint E work is authorized by this run.
- No Checkpoint F cleanup is authorized by this run.
- Phase 6 was not started.

Next narrow hardening run:

- Track external alpha tester evidence in GitHub issue #1: https://github.com/stefan-mcf/shyftr/issues/1
- Send the Wave 1 tester packet to 3-5 technical testers.
- Before outreach, rerun Wave 0 gates and tell testers to record the exact SHA from `git rev-parse HEAD`.
- Prefer the GitHub alpha test report template for returned results: `.github/ISSUE_TEMPLATE/alpha_test_report.md`.
- Record each returned result in the Wave 3 table.
- Re-run Wave 0 gates on the exact SHA if any tracked files change before tester outreach.
- Close or split Tranche 8.5 only after the external evidence threshold is met or the remaining proof is explicitly rescoped.
