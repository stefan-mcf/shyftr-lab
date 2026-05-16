# ShyftR Phase 8 (Evaluation Track) Tranched Plan

Date: 2026-05-15
Repo: `/Users/stefan/ShyftR`
Status: ready to start after Phase 7 completion

Important naming note:
- This plan uses the label `Phase 8 (Evaluation Track)`.
- `docs/status/tranched-plan-status.md` already records an older implementation-track item named `Phase 8 productization` as closed.
- This artifact is not reopening that closed implementation-track phase. It is a new post-Phase-7 evaluation-track plan grounded in `broad-roadmap-concept.md` lines 459-539.

## Goal

Build a hardened, reproducible, public-safe evaluation track that measures what ShyftR already implements today and then extends that measurement surface carefully toward the broad-roadmap Phase 8 target: full-system evaluation and a frontier-readiness report.

The first duty of this plan is honesty:
- unify existing evaluation, metrics, hygiene, audit, and frontier-foundation surfaces into one canonical bundle;
- separate deterministic local proxy metrics from real task-quality claims;
- keep all evidence synthetic or operator-approved;
- avoid hosted, multi-tenant, production, or context-window-expansion claims.

## Authoritative grounding

Read first:
- `/Users/stefan/ShyftR/2026-05-15-shyftr-phase-7-closeoff.md`
- `/Users/stefan/ShyftR/broad-roadmap-concept.md` (especially lines 459-539)
- `/Users/stefan/ShyftR/docs/status/current-implementation-status.md`
- `/Users/stefan/ShyftR/docs/status/current-state-baseline-closeout.md`
- `/Users/stefan/ShyftR/docs/status/current-state-harness-surface-inventory.md`
- `/Users/stefan/ShyftR/docs/status/phase-10-local-evaluation-closeout.md`
- `/Users/stefan/ShyftR/docs/status/tranched-plan-status.md`

Current truth anchors in code:
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

## Current starting truth

Phase 7 is complete and intentionally stopped before benchmark or frontier-readiness claims.

Already implemented and usable:
1. Current-state baseline harness
   - synthetic, repo-local, temp-cell scoped
   - canonical regression contract at `docs/status/current-state-baseline-summary.json`
2. Deterministic local evaluation metrics
   - `metrics.py` exposes retrieval/effectiveness/health summaries
   - precision/recall/F1 values are explicitly proxy metrics, not external task-evaluation claims
3. Safety visibility surfaces
   - `audit_summary(...)`
   - `hygiene_report(...)` with `audit_findings`
4. Frontier foundations
   - confidence baseline, graph, simulation, retrieval modes, reputation, regulator proposals, eval generation
5. Local readiness and observability surfaces
   - readiness reports, diagnostic summaries, retrieval logs, token/latency telemetry

Not yet implemented as a canonical Phase 8 surface:
- one full-system evaluation runner;
- one canonical ablation report schema;
- one frontier-readiness report generator;
- one latency/throughput contract for repeatable comparison;
- one explicit evaluation-track closeout bundle.

## Non-negotiable scope boundary

### In scope
- unify existing local evaluation surfaces into one canonical evaluation-track runbook and report bundle;
- add deterministic harness plumbing needed to compare already-implemented ShyftR layers;
- add synthetic fixtures that answer broad-roadmap Phase 8 questions where practical;
- add clear report schemas, stop boundaries, and evidence wording rules;
- add local informational latency/throughput measurement where stable enough to be useful;
- produce canonical plan, closeoff, and handoff artifacts for continuation.

### Out of scope unless separately approved later
- hosted or multi-tenant claims;
- production-readiness claims;
- package-release or market-superiority claims;
- private-core evaluators, private ranking, or hidden benchmark heuristics;
- real customer, employer, family, or regulated data;
- nondeterministic external benchmark pipelines by default;
- architecture expansion disguised as evaluation work;
- saying ShyftR expands provider context windows.

## Public wording rules for this phase

Use these phrases:
- `baseline harness`
- `regression harness`
- `deterministic proxy metrics`
- `frontier foundations`
- `frontier review surfaces`
- `local-first evaluation bundle`
- `synthetic or operator-approved evidence`

Avoid these phrases unless later evidence truly supports them:
- `frontier-grade`
- `frontier-ready` as an unqualified claim
- `production-ready`
- `benchmark winner`
- `expands hard context window`
- `real-world performance` unless the evidence actually covers real-world tasks

## Core design policy

1. Orchestration before invention.
   - First unify the evaluation surfaces that already exist before adding new benchmark tracks.

2. Evidence before wording.
   - Public claims must be derived from measured outputs, not architecture aspirations.

3. Synthetic-first by default.
   - Temp cells, synthetic fixtures, and repo-local evidence remain the default proof basis.

4. Additive-only evaluation plumbing.
   - Phase 8 should not silently widen write authority or redesign memory semantics.

5. Stable contracts beat flashy metrics.
   - A smaller reproducible bundle is better than a broad but unstable benchmark story.

## Safe defaults

1. Call this work `Phase 8 (Evaluation Track)` everywhere.
2. Treat `docs/status/current-state-baseline-summary.json` as the current machine-comparable regression contract until a broader contract is explicitly added.
3. Treat `metrics.py` retrieval-quality numbers as proxy metrics only.
4. Treat latency/throughput numbers as informational until repeated runs show acceptable local stability.
5. Keep service-backed evaluation optional; CLI/script paths are the default canonical route.
6. Prefer temp-cell and fixture-driven runs over direct mutation of user cells.
7. Every new evaluation artifact must state what it proves and what it does not prove.

## Proposed tranche sequence

### Tranche P8-0: evaluation-track kickoff and schema lock
Objective:
- freeze the Phase 8 evaluation vocabulary, report schema, command set, and non-claims before writing new harness code.

Deliverables:
- this canonical plan;
- a canonical handoff packet;
- a fixed report outline for future evaluation bundles;
- a naming-collision note distinguishing evaluation-track Phase 8 from the closed productization label in `docs/status/tranched-plan-status.md`.

Acceptance criteria:
- the plan clearly separates existing truth from future work;
- exact repo commands are pinned;
- no benchmark or frontier-readiness claim is made yet.

Stop boundary:
- do not add new code in this tranche.

### Tranche P8-1: canonical evaluation bundle runner
Objective:
- create one reproducible runner that gathers the current-state baseline, metrics summary, hygiene report, audit summary, and frontier snapshot into one local bundle.

Likely file touchpoints:
- `scripts/`
- `src/shyftr/cli.py`
- possibly a new `src/shyftr/reports/` helper
- tests under `tests/test_phase8_*`

Required outputs per run:
- git SHA
- timestamp
- python version
- command manifest
- baseline summary path
- metrics summary payload
- hygiene payload
- audit summary payload
- frontier surface snapshot
- explicit `claims_allowed` / `claims_not_allowed` block

Acceptance criteria:
- deterministic rerun shape;
- no writes outside temp cells or chosen output directory;
- full repo verification remains green.

Stop boundary:
- no retrieval algorithm changes;
- no new authority behavior;
- no hidden network calls.

### Tranche P8-2: ablation harness for already-implemented layers
Objective:
- compare the memory-system layers that already exist and can be measured honestly now.

Minimum comparison rows:
- no memory
- durable memory only
- durable + continuity
- durable + continuity + live context
- current implemented frontier foundations snapshot

Stretch rows only if practical and still local/deterministic:
- long-context-only baseline
- vanilla RAG baseline

Acceptance criteria:
- each row is defined by a reproducible command path or a clearly documented `not yet practical` note;
- comparison tables distinguish actual measured rows from deferred rows.

Stop boundary:
- if a row requires external services, private data, or unstable harnesses, defer it explicitly.

### Tranche P8-3: fixture expansion aligned to broad-roadmap questions
Objective:
- add synthetic fixtures for the broad-roadmap Phase 8 questions that are not answered by the current baseline harness.

Focus areas:
- continuity/resume value
- harmful-memory survival and contradiction visibility
- harvest classification behavior
- stale/duplicate-memory hygiene
- token budget tradeoffs under fixed bounded packs

Acceptance criteria:
- all fixtures remain synthetic;
- expected outputs are machine-comparable;
- failures can represent honest weaknesses rather than harness breakage.

Stop boundary:
- do not introduce benchmark theater or padded fixtures that bias results.

### Tranche P8-4: latency and throughput measurement contract
Objective:
- add a bounded local performance track for append, pack, and selected rebuild/report operations.

Candidate measures:
- append latency
- pack latency p50/p95
- retrieval-log growth volume
- report generation latency
- index rebuild time if a rebuildable index path is in scope and stable enough
- token cost / pack-size summaries from existing observability data

Acceptance criteria:
- metric definitions are explicit;
- local variability caveats are documented;
- regression comparisons are possible without overclaiming universal performance.

Stop boundary:
- do not turn unstable machine-specific numbers into hard pass/fail gates unless stability is proven first.

### Tranche P8-5: frontier-readiness report assembly
Objective:
- produce the canonical public-safe Phase 8 report that says what is implemented, what is measured, what is not yet measured, and what the evidence actually supports.

Required sections:
- implemented surfaces inventory
- ablation table
- proxy metrics table
- hygiene and safety signals
- latency/throughput notes
- limitations
- claim boundaries
- next-research backlog

Acceptance criteria:
- every positive statement points to measured evidence;
- every important missing measure is called out plainly;
- public wording matches measured truth.

Stop boundary:
- no unqualified frontier-grade, hosted, or production wording.

### Tranche P8-6: optional external benchmark adapters
Objective:
- only if explicitly approved later, add external public benchmark adapters after the internal evaluation bundle is stable.

Possible candidates from the roadmap:
- LoCoMo
- LongMemEval
- LongBench
- synthetic screenshot/resource QA

Acceptance criteria:
- licensing, reproducibility, and public-safe boundaries are clear;
- imported datasets do not silently become canonical truth.

Stop boundary:
- if reproducibility, licensing, or privacy becomes messy, do not land this tranche.

## Command contract

Preflight and repo verification:
```bash
cd /Users/stefan/ShyftR && git status --short --branch
cd /Users/stefan/ShyftR && PYTHONPATH=.:src pytest -q
cd /Users/stefan/ShyftR && PYTHONPATH=.:src python -m compileall -q src scripts examples
cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-public-stale
cd /Users/stefan/ShyftR && python scripts/terminology_inventory.py --fail-on-capitalized-prose
cd /Users/stefan/ShyftR && python scripts/public_readiness_check.py
cd /Users/stefan/ShyftR && git diff --check
```

Current baseline harness commands:
```bash
cd /Users/stefan/ShyftR && python scripts/current_state_baseline.py --mode durable
cd /Users/stefan/ShyftR && python scripts/current_state_baseline.py --mode carry
cd /Users/stefan/ShyftR && python scripts/current_state_baseline.py --mode live
cd /Users/stefan/ShyftR && python scripts/current_state_baseline.py --mode all
cd /Users/stefan/ShyftR && python scripts/compare_current_state_baseline.py docs/status/current-state-baseline-summary.json docs/status/current-state-baseline-summary.json
```

Current metrics/safety snapshot commands to preserve in future tranches:
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

## Minimum new test policy for implementation tranches

When Phase 8 code work starts, add focused tests first.
Likely first-wave files:
- `tests/test_phase8_evaluation_bundle.py`
- `tests/test_phase8_ablation_harness.py`
- `tests/test_phase8_latency_contract.py`
- targeted updates to existing baseline/metrics/audit/hygiene tests only when truly needed

Each tranche should prove:
- deterministic output shape;
- synthetic-only or clearly operator-approved evidence;
- no hidden writes to user cells;
- claims text stays within the public wording rules.

## Risks to watch

1. Naming collision risk
- `Phase 8` already means something else in `docs/status/tranched-plan-status.md`.
- Every artifact in this stream must say `Phase 8 (Evaluation Track)`.

2. Proxy-metric inflation
- retrieval quality values in `metrics.py` are useful but not task-success proof.

3. Benchmark theater
- a large table with weak semantics is worse than a smaller honest bundle.

4. Hidden scope expansion
- evaluation work must not quietly become retrieval redesign or hosted-product work.

5. Machine-variance confusion
- local latency numbers may be useful for comparison but not universal truth.

## Deliverables expected before final closeout

At the end of this phase, the repo should have:
- canonical Phase 8 evaluation-track plan
- canonical Phase 8 handoff packet
- evaluation bundle runner or equivalent report-generation path
- ablation report with explicit deferred rows where needed
- latency/throughput notes with local-only caveats
- frontier-readiness report with limitations and claim boundaries
- final closeout artifact with exact verification commands and results

## One-line execution summary

Proceed by turning the existing baseline, metrics, hygiene, audit, readiness, and frontier-foundation surfaces into one honest, reproducible `Phase 8 (Evaluation Track)` bundle before attempting broader benchmark claims.