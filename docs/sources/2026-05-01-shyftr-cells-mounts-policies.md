# ShyftR cells, Mounts & Policies

> Source: operator-local concept document, sanitized into this public note.
> Converted from PDF to Markdown for repository reference. Source PDF pages: 4.

This document describes the design of ShyftR cells and the policy framework that governs how they ingest evidence, promote memory, retrieve context and learn from feedbacks. It also introduces the concept of mounts, which attach cells to specific layers of a runtime or organisation.

## What Is a cell?

A cell is the fundamental unit of memory in ShyftR. Each cell encapsulates its own append-only ledgers (evidences.jsonl, candidates.jsonl, memories/approved.jsonl, feedbacks.jsonl, etc.) and retrieval indexes under grid/. cells are isolated by default: memory written to one cell is not automatically visible to another. You can create as many cells as needed to model different scopes:

- Global rules cell – holds shared guardrules and high-authority rules applicable across domains.

- User cell – captures a user’s preferences and recurring workflows.

- Project cell – stores project-specific facts, architecture decisions and conventions.

- Sector cell – holds knowledge relevant to a runtime sector (development, documentation,

review, research, etc.).

- Agent cell – tracks the quirks and behaviours of a particular agent role or model.

- Task cell – temporary context for a single task; it can be archived or distilled later.

## Mounts

A mount attaches a cell to a particular runtime layer and defines how it behaves. Each mount includes configuration for ingestion, retrieval, learning and privacy. A mount can attach a cell to: A runtime system (e.g. Antaeus/Hermes). A sector within a runtime (dev, docs, review). A project or domain. A specific agent or user.

### Mount Configuration Fields

Below is an example of a mount configuration. Names and fields may evolve, but the pattern illustrates the concept:

```text
mount_id: antaeus-dev-sector
cell_id: antaeus/dev
attached_to_type: sector
attached_to_id: dev
scope: project_conflux
input_adapters:
- task_closeout
- review_result
- tool_error
retrieval_policy:
mode: balanced
max_items: 12
include_cells:
- global/rule
- user/stefan
- project/conflux
- sector/dev
learning_policy:
auto_ingest: true
auto_extract_candidates: true
auto_promote: false
promotion_policy:
require_review: true
feedback_policy:
require_feedback_report: true
privacy_policy:
allow_cross_cell_resonance: true
allow_raw_evidence_export: false
```

Each field describes a different aspect of the mount:

- input_adapters – Which sources of evidence the cell should consume (closeouts, logs,

documents, chat transcripts, etc.).

- retrieval_policy – How packs are constructed: number of items, retrieval mode (conservative/

balanced/exploratory), and which other cells to include.

- learning_policy – Whether to automatically ingest evidences and extract candidates, and whether to

auto-promote certain kinds of candidates (e.g. explicit remember calls). By default auto_promote is false to require review.

- promotion_policy – Specifies when a candidate can be promoted to a memory. Even in trusted

modes, promotion events must be recorded in ledgers with provenance.

- feedback_policy – Defines whether an feedback report is mandatory after pack use and how feedbacks

affect confidence or affinity.

- privacy_policy – Governs cross-cell sharing and raw evidence export. It determines whether a cell

can export its approved memory or allow resonance with other cells and whether raw evidence can leave the cell.

## Default Behaviour

By default a newly mounted cell should behave as follows:

- Auto-Ingest evidences – Listen to the configured adapters and append evidence to

evidences.jsonl.

- Auto-Extract candidates – Run extraction routines to propose candidates from each evidence and append

them to candidates.jsonl.

- Require Review for Promotion – Do not auto-promote candidates to memories unless explicitly

allowed (e.g. trusted remember calls). Review events must be recorded.

- Serve packs Automatically – When a pack is requested, select relevant memories from the cell

and any included cells according to the retrieval policy and compile them into a structured pack.

- Record feedbacks – Require a feedback after pack use, capturing applied, useful, harmful, ignored,

contradicted, over-retrieved and missing memory. feedbacks update confidence and retrieval affinity via event ledgers.

- Never Mutate the Past – All changes to memory must be append-only. Confidence and affinity

updates are recorded as events rather than overwriting original memories.

## Policies Explained

### Learning Policy

The learning policy controls how far automated ingestion goes. There are three levels:

- Passive learning – evidences are ingested but no candidates are extracted. Use this for early

observation.

- candidate learning – evidences and candidates are ingested, but promotion requires review. This is the

safe default for new mounts.

- Trusted learning – Certain inputs (explicit remember calls, verified runtime rules) bypass

review and automatically become memories, provided the regulator allows it. Use sparingly.

### Retrieval Policy

The retrieval policy defines how to compile packs. Key parameters include:

- Mode – Conservative (high-confidence only), Balanced (default), Exploratory (include lower

confidence), Risk-Averse (amplify caution items), Audit (include challenged/isolated memory with warnings).

- Max items – The maximum number of memory items in a pack. Helps manage context window

budgets.

- Include cells – Other cells whose memories may be retrieved. For example, a sector cell may

include the global rules cell and the user cell.

### Promotion Policy

Promotion policies specify whether candidates can be auto-promoted and under what conditions. Even when auto-promotion is enabled, a review event should still be written to the ledger documenting the decision. Typical policies are:

- Manual promotion only – All candidates require review.

- Trusted path promotion – candidates extracted from trusted input adapters may be promoted

automatically.

- Kind-based promotion – Certain candidate kinds (e.g. verification heuristics) may be auto-promoted

while others (e.g. cautionary guidance) must be reviewed.

### feedback Policy

feedback policies govern what happens when a feedback is recorded. For example, a policy might specify that confidence updates require multiple positive or negative feedbacks before changing the belief, or that retrieval affinity decays more quickly on harmful misses. feedback policies can differ by cell to reflect domain-specific caution. 5. 6.

### Privacy Policy

Privacy policies control what a cell can export or share. They may include:

- Visibility tiers – Public, internal, private, secret.

- Cross-cell resonance – Whether patterns from this cell can influence others.

- Raw evidence export – Whether raw evidence can be shared across cells (often disallowed for

sensitive data).

- Role-based access – Which users or agents may request packs from the cell.

## Best Practices

Create Separate cells for Distinct Contexts – Avoid mixing project, user and sector knowledge in one cell. This keeps retrieval precise and minimises contamination.

- Prefer candidate Learning First – Start with auto-ingest and candidate extraction but require

review before promotion. Enable auto-promotion gradually for trusted data sources.

- Regularly Review Policies – Use metrics and pilot data to adjust learning, retrieval and

promotion policies. Overly strict policies will stall memory growth; overly permissive policies will pollute memory.

- Treat cells as Modules – Each cell should be attachable, detachable and migratable. Backups,

migrations and federation should operate at the cell level.

## Summary

ShyftR cells encapsulate memory for a specific scope and become useful when attached to runtime layers via mounts. Mount configuration defines how the cell ingests evidences, extracts candidates, promotes memories, retrieves packs and learns from feedbacks. Policies provide fine-grained control over automation and sharing. By following these guidelines, cells can be safely plugged into agent systems, automatically ingest evidence and learn over time without compromising trust or privacy.
