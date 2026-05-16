# ShyftR Phase 8 (Evaluation Track) Handoff Packet

Date: 2026-05-15
Repo: /Users/stefan/ShyftR
Recorded: 2026-05-15 20:08:33 AEST
Status: ready to continue from grounded planning truth
Resume from this exact truth.

Canonical planning artifact:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-8-evaluation-track-tranched-plan.md`

Canonical predecessor:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-closeoff.md`

Roadmap definition source:
- `/Users/stefan/ShyftR/broad-roadmap-concept.md` lines 459-539

## What is already complete and proven

1. Phase 7 is complete and closed.
   - Privacy, policy, contradiction-safety, and audit/hygiene visibility hardening landed.
   - Phase 7 explicitly stopped before benchmark or frontier-readiness claims.

2. The repo already has meaningful evaluation-related surfaces.
   - Current-state baseline harness:
     - `scripts/current_state_baseline.py`
     - `scripts/compare_current_state_baseline.py`
     - canonical machine-comparable contract at `docs/status/current-state-baseline-summary.json`
   - Deterministic local evaluation metrics:
     - `src/shyftr/metrics.py`
   - Safety/reporting surfaces:
     - `src/shyftr/audit.py`
     - `src/shyftr/reports/hygiene.py`
   - Frontier foundations:
     - `src/shyftr/frontier.py`
     - `src/shyftr/evalgen.py`
     - `src/shyftr/simulation.py`
   - Readiness/diagnostics/console/service surfaces:
     - `src/shyftr/readiness.py`
     - `src/shyftr/observability.py`
     - `src/shyftr/console_api.py`
     - `src/shyftr/server.py`

3. Deep-research grounding for the next move is complete.
   - A bounded swarm lane reviewed repo truth and recommended a hardened tranche shape.
   - The controller grounded that advice against live repo files and produced the canonical plan.

4. Current repo health is suitable for continuation planning.
   - Swarm deep-research run rechecked repo tests and reported:
     - `cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q`
     - result: `985 passed, 31 warnings`

## Current truth boundary

This handoff is for continuing the new `Phase 8 (Evaluation Track)` only.

Important naming collision:
- `docs/status/tranched-plan-status.md` already says `Phase 8 productization` is closed.
- That older label belongs to the completed implementation-track status document.
- This handoff and its paired plan are about a different stream: the broad-roadmap Phase 8 goal of full-system evaluation and frontier-readiness reporting.
- Every continuation artifact should keep the exact label `Phase 8 (Evaluation Track)`.

## What is not yet implemented

The following still do not exist as canonical repo-level deliverables:
- one unified full-system evaluation runner;
- one canonical ablation report schema;
- one canonical frontier-readiness report generator;
- one formal latency/throughput comparison contract for this evaluation stream;
- one final Phase 8 evaluation closeout bundle.

## Key design decisions already made

1. Orchestration before invention.
   - The next step is to unify existing baseline, metrics, hygiene, audit, readiness, and frontier-foundation surfaces.
   - Do not start by redesigning retrieval or memory architecture.

2. Proxy metrics must stay clearly labeled.
   - `metrics.py` retrieval-quality values are deterministic proxy metrics derived from retrieval logs and outcomes.
   - They are useful evidence, but not real task-success proof.

3. Synthetic-first and local-first remain the default proof posture.
   - Temp cells and synthetic fixtures are the default evidence base.
   - External benchmarks are later and optional, not the first move.

4. The current baseline harness remains the anchor.
   - `docs/status/current-state-baseline-summary.json` is the current machine-comparable regression contract until a broader one is explicitly added.

5. Frontier wording must remain disciplined.
   - Use `frontier foundations` and `frontier review surfaces` unless measured evidence later supports stronger phrasing.

## Exact ordered continuation sequence

1. Preflight the repo again.
   - Confirm repo path is `/Users/stefan/ShyftR`.
   - Confirm branch/worktree with live `git status --short --branch`.
   - Read the Phase 7 closeoff, the Phase 8 evaluation-track plan, and this handoff packet first.

2. Start with Tranche P8-1 only.
   - Do not jump directly to external benchmarks, hosted-style claims, or broad performance storytelling.
   - The first implementation slice is the canonical evaluation bundle runner.

3. Write focused failing tests first.
   Minimum first wave:
   - bundle runner emits deterministic top-level keys;
   - bundle captures baseline summary reference/path;
   - bundle captures metrics summary payload;
   - bundle captures hygiene and audit summary payloads;
   - bundle captures a frontier snapshot or clearly records that snapshot path/shape;
   - bundle includes explicit `claims_allowed` and `claims_not_allowed` blocks;
   - bundle writes only inside the selected output area or temp cells.

4. Implement the smallest additive code to make P8-1 green.
   Likely touchpoints:
   - `scripts/`
   - `src/shyftr/cli.py`
   - maybe a new helper under `src/shyftr/reports/`
   - focused new tests under `tests/test_phase8_*`

5. Verify P8-1 before opening the ablation tranche.
   Focused gates should include:
   - targeted Phase 8 tests
   - existing baseline harness tests
   - existing metrics, hygiene, and audit tests if touched

6. After P8-1, move to P8-2.
   - Build the comparison table only for already-implemented or honestly-deferrable rows:
     - no memory
     - durable memory only
     - durable + continuity
     - durable + continuity + live context
     - current implemented frontier foundations snapshot
   - Treat long-context-only and vanilla-RAG rows as stretch rows only if they remain local, deterministic, and honest.

7. Only after the bundle and ablation layers are stable, open later tranches.
   - P8-3 fixture expansion
   - P8-4 latency/throughput contract
   - P8-5 frontier-readiness report assembly
   - P8-6 optional external benchmark adapters only if explicitly approved later

8. Before any closeout artifact, rerun full repo verification.
   - full pytest
   - compileall
   - terminology inventory checks
   - public readiness
   - `git diff --check`

## Canonical command set to preserve

Preflight and verification:
```bash
cd /Users/stefan/ShyftR && git status --short --branch
cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q
cd /Users/stefan/ShyftR && PYTHONPATH=.:src python -m compileall -q src scripts examples
cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-public-stale
cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-capitalized-prose
cd /Users/stefan/ShyftR && python scripts/public_readiness_check.py
cd /Users/stefan/ShyftR && git diff --check
```

Baseline harness commands:
```bash
cd /Users/stefan/ShyftR && python scripts/current_state_baseline.py --mode durable
cd /Users/stefan/ShyftR && python scripts/current_state_baseline.py --mode carry
cd /Users/stefan/ShyftR && python scripts/current_state_baseline.py --mode live
cd /Users/stefan/ShyftR && python scripts/current_state_baseline.py --mode all
cd /Users/stefan/ShyftR && python scripts/compare_current_state_baseline.py docs/status/current-state-baseline-summary.json docs/status/current-state-baseline-summary.json
```

Existing evaluation/safety snapshot commands:
```bash
shyftr metrics <cell_path>
shyftr hygiene <cell_path>
shyftr audit list <cell_path> --summary
shyftr evalgen <cell_path>
shyftr simulate <cell_path> <query> --current-mode balanced --proposed-mode conservative
```

Optional local service snapshot path:
```bash
shyftr serve --host 127.0.0.1 --port 8014
curl http://127.0.0.1:8014/v1/health
curl "http://127.0.0.1:8014/frontier?cell_path=<cell_path>"
```

## Do-not-redo / non-goals

Do not redo:
- Phase 7 implementation work;
- generic deep research on what Phase 8 should mean;
- already-grounded repo inventory work unless a repo change invalidates it.

Do not do in P8-1:
- retrieval redesign;
- authority/policy expansion;
- external benchmark ingestion by default;
- hosted-service or production storytelling;
- unqualified frontier-readiness claims.

## Known risks to watch during implementation

1. Naming drift
- forgetting the `Evaluation Track` qualifier will create contradictions with existing status docs.

2. Metric inflation
- proxy metrics can be accidentally narrated as real task-success metrics.

3. Benchmark theater
- broad tables without reproducible semantics will weaken the repo rather than strengthen it.

4. Hidden architecture creep
- evaluation code can easily turn into retrieval or schema work unless scope is pinned.

5. Local-performance overclaiming
- machine-specific latency numbers are useful comparison hints, not universal performance truth.

## Read-first file set for the next operator

Planning / truth artifacts:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-closeoff.md`
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-8-evaluation-track-tranched-plan.md`
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-8-evaluation-track-handoff-packet.md`
- `/Users/stefan/ShyftR/broad-roadmap-concept.md`
- `/Users/stefan/ShyftR/docs/status/tranched-plan-status.md`

Evaluation truth anchors:
- `/Users/stefan/ShyftR/docs/status/current-state-baseline-closeout.md`
- `/Users/stefan/ShyftR/docs/status/current-state-harness-surface-inventory.md`
- `/Users/stefan/ShyftR/docs/status/phase-10-local-evaluation-closeout.md`
- `/Users/stefan/ShyftR/docs/status/current-implementation-status.md`

Core code:
- `/Users/stefan/ShyftR/scripts/current_state_baseline.py`
- `/Users/stefan/ShyftR/scripts/compare_current_state_baseline.py`
- `/Users/stefan/ShyftR/src/shyftr/metrics.py`
- `/Users/stefan/ShyftR/src/shyftr/frontier.py`
- `/Users/stefan/ShyftR/src/shyftr/evalgen.py`
- `/Users/stefan/ShyftR/src/shyftr/simulation.py`
- `/Users/stefan/ShyftR/src/shyftr/audit.py`
- `/Users/stefan/ShyftR/src/shyftr/reports/hygiene.py`
- `/Users/stefan/ShyftR/src/shyftr/readiness.py`
- `/Users/stefan/ShyftR/src/shyftr/observability.py`
- `/Users/stefan/ShyftR/src/shyftr/console_api.py`
- `/Users/stefan/ShyftR/src/shyftr/server.py`

## Recommended next user-facing command of work

Proceed optimally into `Phase 8 (Evaluation Track)` Tranche P8-1:
- write the focused failing bundle-runner tests first
- implement the smallest additive evaluation bundle runner
- verify it against the pinned repo command contract
- only then open ablation work

## One-line summary

Phase 8 should continue by turning the existing baseline, metrics, hygiene, audit, readiness, and frontier-foundation surfaces into one honest, reproducible evaluation bundle before attempting broader benchmark or frontier-readiness claims.
