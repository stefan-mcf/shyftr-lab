# Universal memory Substrate

ShyftR is the local-first memory substrate for agents, assistants, projects, teams, and long-running knowledge work. It provides durable memory cells with provenance, review gates, retrieval, packs, feedbacks, profiles, import/export, and knowledge projections.

This scope keeps ShyftR focused. ShyftR remains a memory substrate rather than an orchestrator, execution runtime, hosted note application, project-management system, or vector database product. External systems may capture activity, execute work, present notes, render dashboards, or accelerate retrieval. ShyftR owns the durable memory record and the rules for turning experience into trusted memory.

## Product boundary

The universal substrate scope is:

- Local-first cell ledgers for canonical memory truth.
- regulator-controlled admission, promotion, retrieval, mutation, and export.
- grid indexes that accelerate retrieval and can be rebuilt from ledgers.
- packs, profiles, markdown pages, dashboards, summaries, and documents as projections or applications.
- Optional adapters for capture, sync, import, export, search, and review surfaces.
- Product-neutral compatibility contracts for assistant-memory providers and knowledge workspaces.

ShyftR should absorb durable memory responsibilities from broad tool categories while leaving operational responsibilities with the systems that already perform them. Execution runtimes still execute. Note editors still edit. Document systems still display and collaborate. Retrieval backends still index. ShyftR keeps the canonical ledger, provenance, review history, lifecycle state, and exportable memory substrate.

## Canonical truth model

The truth model is fixed:

```text
evidence -> candidate -> memory -> pattern -> rule
```

- evidences are raw experience and imported evidence.
- candidates are extracted memory proposals.
- memories are reviewed durable memories.
- patterns are recursively distilled patterns.
- rules are shared high-confidence rules.

The operational rule remains:

```text
cell ledgers are truth.
The regulator controls admission, promotion, retrieval, mutation, and export.
The grid is acceleration.
The pack is application.
feedback is learning.
memory confidence is evolution.
Profiles, documents, dashboards, and markdown pages are projections.
```

Generated artifacts can be deleted and rebuilt. Ledger history remains the authoritative record for memory, provenance, status, review, mutation, and confidence.

## Compatibility targets

The first compatibility target is agent memory providers: systems that store assistant preferences, profile facts, searchable memories, or task-relevant context. ShyftR compatibility for that category is defined in `memory-provider-contract.md`.

The second compatibility target is knowledge workspaces: systems that store notes, documents, backlinks, topic pages, project pages, and review surfaces. ShyftR compatibility for that category is defined in `knowledge-workspace-contract.md`.

Both targets use category-level contracts. Public ShyftR docs should describe provider and workspace capabilities rather than compare against named products.

## Replacement shape

ShyftR replaces durable memory authority, not every surface around memory.

| Category capability | ShyftR-native equivalent | Canonical truth |
|---|---|---|
| Remember a fact or preference | evidence capture, candidate extraction, reviewed memory promotion | cell ledgers |
| Search durable memory | Hybrid retrieval through the grid | cell ledgers, with rebuildable indexes |
| Build an assistant profile | Profile projection from reviewed memories and rules | cell ledgers |
| Provide task context | pack assembled through the regulator | cell ledgers plus retrieval logs |
| Record whether context helped | feedback and confidence events | cell ledgers |
| Forget or replace memory | Append-only lifecycle, supersession, redaction, and exclusion events | cell ledgers |
| Import an existing memory export | Product-neutral import as evidences plus provenance | cell ledgers |
| Export memory | Snapshot and markdown projections | cell ledgers remain authoritative |
| Maintain notes or documents | Ingest, sync, projection, backlinks, and review queues | cell ledgers |
| Render dashboards or pages | Optional generated projections | Rebuildable projection |

## Non-goals for the substrate core

The core should avoid taking ownership of unrelated execution and presentation roles:

- Running agent tasks or worker queues.
- Replacing every note editor interface.
- Becoming a hosted collaboration suite.
- Treating a vector index as canonical storage.
- Hiding provenance behind opaque profile text.
- Letting generated markdown or dashboards replace ledgers.
- Binding compatibility to a named memory provider or note workspace.

These capabilities may attach as optional modules, adapters, or projection surfaces when they serve the cell ledger model.

## Implementation implications

Future implementation work slices should stay small and contract-first:

1. Define the compatibility contract.
2. Add ShyftR-native data models or APIs.
3. Preserve append-only ledger provenance.
4. Keep adapters optional.
5. Treat generated files as projections.
6. Test import/export and lifecycle semantics without requiring external services.

The universal substrate arc succeeds when assistant runtimes and knowledge workflows can rely on ShyftR cells as their durable local memory authority while still choosing their own execution, editing, display, and retrieval-acceleration tools.
