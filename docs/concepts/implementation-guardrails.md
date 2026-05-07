# ShyftR Implementation Guardrules

Status: implementation rule. Use this file as a guardrule before starting or reviewing any ShyftR work slice, especially the Universal memory Substrate follow-up plan.

Purpose: keep ShyftR ambitious without letting it become a bloated monolith. ShyftR may grow many adapters and projections, but the core must remain a small, stable, local-first memory-cell substrate.

---

## Core product definition

ShyftR is an attachable recursive memory-cell substrate.

ShyftR remains a memory substrate rather than a task runner, agent orchestrator, hosted note app, vector database product, project-management system, or live execution-state store.

The canonical core is:

```text
candidate -> memory -> pattern -> rule
```

Supporting core concepts:

- cell
- regulator
- cell ledger
- grid
- pack
- feedback
- Proposal
- append-only truth
- provenance
- review gates
- retrieval
- confidence evolution
- mutation lifecycle
- portability

Everything else must attach to this core as an adapter, projection, importer, exporter, workspace, or optional module.

---

## Golden rule

```text
cell ledgers are truth.
The regulator controls admission, promotion, retrieval, and export.
The grid is acceleration.
The pack is application.
feedback is learning.
memory confidence is evolution.
Markdown and dashboards are projections.
External runtimes apply; ShyftR proposes.
```

Do not weaken this rule to make an integration easier.

---

## Thin core, attachable modules

Keep the core package focused on durable memory.

Core package responsibilities:

- models
- cell layout
- append-only ledgers
- regulator policy
- evidence ingest primitives
- candidate extraction primitives
- review and promotion
- retrieval and pack assembly
- feedback and confidence evolution
- distillation into patterns and rule proposals
- mutation events such as supersession, deprecation, quarantine, and redaction projection
- profile projections
- backup, restore, validation, and migration safety

Optional module responsibilities:

- runtime adapters
- assistant adapters
- managed memory importers
- markdown note ingest
- markdown or HTML export
- document and research ingest
- review CLI, TUI, or UI
- dashboard surfaces
- optional vector backend adapters
- external workspace sync

If a feature captures, displays, imports, exports, syncs, or reviews memory, it should usually be an optional module.

If a feature strengthens the lifecycle, provenance, packs, feedback, confidence, cell boundaries, or portability, it may belong near core.

---

## Suggested package boundaries

Recommended organization:

```text
shyftr/
  models.py
  ledger.py
  layout.py
  policy.py
  ingest.py
  extract.py
  review.py
  promote.py
  pack.py
  feedback.py
  confidence.py
  mutations.py
  profile.py
  backup.py
  restore.py
  validation.py

  integrations/
    runtime and assistant adapters

  importers/
    memory export and migration importers

  notes/
    markdown ingest and sync

  exporters/
    markdown, JSON, and future HTML projections

  documents/
    document and research evidence ingestion

  workspace/
    review CLI, TUI, or UI helpers

  retrieval/
    sparse, vector, hybrid, and backend adapters

  cells/
    registry, routing, and policies shared between cells
```

These boundaries are not rigid file mandates, but implementation should preserve the separation they express.

---

## Non-negotiable boundaries

### 1. ShyftR must not become an orchestrator

Do not make ShyftR own:

- task scheduling
- worker dispatch
- active queue state
- branch or worktree ownership
- retries
- live process monitoring
- model/backend switching for execution
- runtime policy mutation by default

External runtimes own execution. ShyftR receives evidences, returns packs, records feedback, and exports Proposals.

### 2. Operational state must not become durable memory

Reject or quarantine transient facts such as:

- task X is in progress
- worker Y owns branch Z
- queue item is waiting
- file `/tmp/example` exists
- tests passed at a specific time without durable lesson context
- artifact paths as standalone memory
- completion logs as standalone memory

Durable memory should capture lessons, preferences, constraints, failure signatures, recovery patterns, workflows, tool quirks, and reviewed rule.

### 3. Generated projections are not truth

Markdown exports, dashboards, profiles, summaries, reports, and indexes are rebuildable projections.

Correct direction:

```text
cell ledger -> projection
```

Allowed evidence direction:

```text
human-authored note -> evidence -> candidate -> review -> memory
```

Dangerous direction:

```text
generated projection -> canonical truth
```

Never let generated markdown, dashboard state, profile summaries, or indexes silently replace ledgers.

### 4. Adapters must stay optional

Core ShyftR must not require:

- a web server
- a hosted service
- an external vector database
- a PDF/OCR stack
- a markdown workspace
- a particular assistant runtime
- a particular task runtime
- a dashboard UI

Optional dependencies should remain optional. Tests for core behavior should run without network access or hosted services.

### 5. Review gates remain meaningful

Automation may discover, extract, cluster, score, propose, and export.

Automation must not silently:

- promote arbitrary durable memories
- promote shared rules
- destructively deprecate memory
- rewrite canonical ledgers
- apply external runtime policy changes

Trusted direct memory paths are allowed only when explicit, auditable, configurable, and still regulator-checked.

---

## Ambition without bloat

The Universal memory Substrate future-work is allowed to be large because it describes an ecosystem around cells, not a bloated core.

Healthy ambition:

- ShyftR replaces managed assistant memory as canonical durable memory.
- ShyftR can ingest human-authored notes as evidences.
- ShyftR can export human-readable markdown knowledge projections.
- ShyftR can produce profiles, packs, feedback, and proposals.
- ShyftR can support many cells and multi-cell resonance.
- ShyftR can become the durable knowledge substrate underneath human and agent tools.

Unhealthy bloat:

- ShyftR becomes a full note-taking application before the core is excellent.
- Every integration becomes mandatory.
- Runtime execution state is stored as memory.
- Generated workspaces become canonical truth.
- UI decisions freeze weak memory abstractions.
- Adapter convenience bypasses provenance or review.

---

## Implementation order bias

Prefer this order when choosing what to build next:

1. memory provider replacement
2. Profile and mutation semantics
3. Persistent retrieval
4. Multi-cell routing
5. Migration/import safety
6. Assistant and agent runtime integration
7. Markdown ingest and export
8. Review workspace
9. Research/document layer
10. UI, maintenance loops, backup hardening, and scale work

Do not build a polished UI before the core provider, profile, mutation, retrieval, routing, and migration paths are proven.

---

## Design review checklist

Before accepting a work slice, ask:

1. Does this preserve cell ledgers as canonical truth?
2. Does this keep generated artifacts as projections?
3. Does this avoid storing operational state as durable memory?
4. Does this preserve provenance from evidence to memory or proposal?
5. Does this keep review gates meaningful?
6. Does this avoid making optional adapters mandatory?
7. Does this strengthen the core lifecycle or clearly live outside core?
8. Does this keep external runtimes responsible for execution?
9. Can indexes and projections be rebuilt from ledgers?
10. Can this be tested without hosted services unless explicitly marked optional?
11. Does it fit the current future-work order, or is it premature UI/integration work?
12. Would removing an external note tool, vector backend, or runtime leave ShyftR core intact?

If the answer to any of these is no, revise the design before implementation.

---

## Module classification rule

Use this rule when deciding where a feature belongs:

```text
Core: durable memory lifecycle, provenance, review, retrieval, pack, feedback, confidence, cell portability.
Module: capture, display, import, export, sync, UI, runtime glue, optional backend.
Projection: generated profile, summary, dashboard, markdown, report, index.
External runtime: execution, queues, workers, live state, retries, operational policy application.
```

When uncertain, start as a module. Promote toward core only after the abstraction is stable and clearly strengthens the lifecycle.

---

## Final product regulator

The desired end state is:

```text
ShyftR owns canonical memory.
Runtimes consume packs and report feedback.
Human tools create evidences and display projections.
cell ledgers remain inspectable, local-first, and portable.
```

This regulator keeps ShyftR powerful without making it overfilled or overcomplicated.
