# ShyftR → Antaeus/Hermes Integration Strategy

> Source: operator-local concept document, sanitized into this public note.
> Converted from PDF to Markdown for repository reference. Source PDF pages: 3.

This document proposes a staged plan for integrating ShyftR with Antaeus/Hermes or a similar agent runtime. Integration should begin early in the development process but progress cautiously from observation to full memory replacement. The stages below align with the implementation plan; stage boundaries correspond to the completion of certain tranches.

## Objectives

Evaluate ShyftR’s utility without disrupting live tasks. Introduce memory guidance gradually, starting at the orchestration layer before per-worker injection. Measure the impact on task success, time saved and operator burden at each stage. Replace legacy memory (e.g. mem0) only after confidence, relevance and learning mechanisms are in place.

## Stage 1 – Shadow Integration

```text
When: after completing Tranches 1.1–1.3 (provider API and pack/feedback contracts).
```

At this point ShyftR has the fundamental APIs to ingest evidence and return packs. Begin by connecting it to the runtime in read-only mode: The runtime forwards task metadata (task ID, sector, role, summary) and closeouts, reviews and failure reports to ShyftR as evidences. ShyftR processes these evidences and returns packs for each task, but the runtime does not use them yet. Operators manually inspect packs for quality and provide feedbacks on task feedbacks. The goal of stage 1 is to observe whether ShyftR can build relevant memory and compile sensible packs from real data without affecting execution.

## Stage 2 – Sector-Manager Advisory Mode

```text
When: after completing Tranche 1.5 (pack compiler and miss learning).
```

ShyftR can now generate structured packs and learn from feedbacks. Connect ShyftR in advisory mode to sector managers: On receiving a task, the sector manager requests a pack from ShyftR and injects the guidance and caution sections into its own planning prompt. ShyftR does not yet replace any existing memory store (mem0) and packs are treated as optional advice. After the task, the sector manager reports a feedback back to ShyftR indicating which memory items were used, useful, harmful, ignored or missing. Focus on a small number of sectors (dev, docs, review) to evaluate how memory guidance affects planning. Avoid injecting packs into every worker at this stage.

## Stage 3 – Worker-Level pack Injection

```text
When: after completing Tranche 1.7 (retrieval affinity) and optionally Tranche 1.8 (HTTP service
```

hardening). Extend pack injection to individual workers: Each worker receives a role-specific pack containing only the guidance and verification sections relevant to its role (developer, documenter, reviewer). packs are smaller than those given to sector managers to avoid context overload. feedbacks are reported per worker, enabling fine-grained learning. Monitor the effect on worker performance and ensure over-retrieval is measured. This stage introduces more risk because memory influences low-level decisions.

## Stage 4 – mem0 Fallback Replacement

```text
When: after completing Tranches 1.6–1.8 (confidence and affinity events, HTTP service) and after at
```

least one successful pilot loop. Make ShyftR the primary memory for sectors while keeping the legacy store as a fallback: When a sector requests memory, ShyftR serves the pack. If ShyftR has insufficient data, the system falls back to mem0. All feedbacks and learning events go to ShyftR. mem0 remains read-only and is gradually deprecated. This stage marks the first point at which ShyftR controls memory decisions. Ensure that operator review queues and hygiene reports are manageable before proceeding.

## Stage 5 – Full Hermes memory Replacement

```text
When: only after a controlled pilot demonstrates consistent improvement and low harm/miss rates.
```

Typically after Phase 2 and parts of Phase 3. Decommission mem0 and rely solely on ShyftR for memory. Conditions for this stage include: pack application and usefulness rates are positive and stable. Harmful memory rates are low and quickly corrected via feedbacks. Missing memory events are infrequent and easily filled by ingestion. Operator burden (review queue size, review time) is acceptable. Backup/restore and ledger verification are implemented (Phase 5). The system can explain why memory was retrieved and provide audit trules for past decisions. Under these conditions, mem0 can be archived and ShyftR becomes Hermes’ canonical durable memory.

## Guidelines for Integration

- Mount cells at Logical Boundaries – Use separate cells for global rules, user preferences,

project facts, sector-specific knowledge and runtime logs. This allows targeted retrieval and avoids polluting memory across domains.

- Start with Observation – Do not inject packs into live tasks until you have validated pack

relevance and measured noise. Use the observation stage to tune extraction and review policies.

- Measure Everything – At every stage, track how many memory items were applied, useful,

harmful, ignored or missed. Use these metrics to decide when to advance to the next stage.

- Keep Review Gates – Even in automated modes, ensure that new memory cannot be silently

promoted to durable memories without review unless explicitly configured as trusted ingestion.

- Iterate Policies – Use pilot data to adjust regulator policies and retrieval weights. Resist the

urge to remove review entirely; memory quality depends on human oversight.

## Summary

The integration strategy emphasises progressive adoption. ShyftR should begin by listening, then advising, then assisting workers, then replacing legacy memory. At each step, measure impact, adjust policies and ensure the system remains explainable and auditable. Only after proving utility and safety should ShyftR become the canonical memory for your agent runtime.
