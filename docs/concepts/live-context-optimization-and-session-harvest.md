# Live context optimization and session harvest

Status: implemented public alpha

ShyftR can help agent runtimes keep active prompts lean without claiming to increase a model's hard context limit. The runtime owns the prompt and mechanical compaction. ShyftR captures useful working context into cells, builds bounded packs when the runtime needs continuity, and harvests durable lessons at session close.

## product frame

Use this public frame:

```text
ShyftR captures live working context into cells, harvests durable lessons at session close, and retrieves bounded packs so agent runtimes can continue work with a leaner active prompt.
```

Avoid numeric context-window claims. ShyftR should be described as a context optimization and memory-governance layer, not as a way to exceed a model provider's context limit.

## cell roles

A runtime can attach three related ShyftR cell roles.

```text
runtime session
  -> live context cell       working context during the session
  -> continuity cell         context-management evidence and feedback
  -> memory cell             reviewed durable memory
```

### live context cell

The live context cell is a working buffer. It captures context that may help the current task continue without keeping every detail in the active prompt.

Examples:

- active goal;
- current plan;
- active files or artifacts;
- current constraints;
- recent decisions;
- failed attempts and recoveries;
- verification evidence;
- unresolved blockers.

The live context cell should be session-scoped or retention-scoped. It should be harvested and closed when the runtime session closes.

### continuity cell

The continuity cell records how context management performed.

Examples:

- context-pressure events;
- continuity pack requests;
- packs returned to the runtime;
- feedback after compaction or resumed work;
- missing-memory notes;
- stale-memory notes;
- promotion proposals;
- synthetic evaluation reports.

The continuity cell can propose changes to durable memory, but it should not silently mutate the memory cell.

### memory cell

The memory cell stores reviewed durable memory. It should receive only safe high-confidence facts, approved memories, and review-gated promotions.

Examples:

- stable user preferences;
- durable project conventions;
- reusable workflows;
- tool quirks;
- verified recovery patterns;
- promoted rules.

## session-close harvest

Session-close harvest classifies the live context cell before the session is discarded, archived, or compacted.

```text
session closes
-> read live context cell
-> compare continuity feedback and memory cell
-> classify entries
-> write closeout evidence
-> write memory promotion proposals
-> write continuity improvement proposals
-> mark live context cell closed
```

Harvest buckets:

| Bucket | Destination | Purpose |
| --- | --- | --- |
| discard | none or temporary audit | remove noise |
| archive | closeout ledger or session archive | preserve reconstruction evidence |
| continuity feedback | continuity cell | improve future packs and compaction support |
| memory candidate | memory cell candidate ledger | review before durable promotion |
| direct durable memory | memory cell | policy-approved high-confidence memory |
| skill proposal | skill or documentation queue | reusable procedure rather than memory |

The harvest operation should be idempotent. It should use session identifiers and content hashes so repeated closeout runs do not duplicate records.

## pack behavior

The runtime should request bounded packs rather than injecting whole cells.

Recommended pack rules:

- query-driven retrieval;
- strict max item and token budgets;
- duplicate suppression against the active prompt;
- provenance on every item;
- trust tier and confidence on every item;
- caution items for stale, harmful, or superseded memory;
- explicit advisory wording unless the operator enables a stronger mode later.

## relationship to runtime continuity provider

Runtime continuity provider and live context optimization are complementary.

| Capability | Trigger | Primary cell | Output |
| --- | --- | --- | --- |
| continuity pack | context pressure or compaction event | continuity cell plus memory cell | bounded advisory pack |
| compaction feedback | after resumed work | continuity cell | useful, ignored, harmful, missing, or stale records |
| live context capture | during work | live context cell | working context entries |
| session harvest | session close | live context cell plus continuity cell | archive records, proposals, durable memory candidates |

The continuity cell should be extended to understand harvest results, but the live context cell should remain a separate role so high-churn working state does not pollute context-management evidence or durable memory.

## modes

| Mode | Behavior |
| --- | --- |
| off | no live capture or harvest |
| shadow | capture and classify, but do not export packs or write durable memory |
| advisory | export bounded packs and write review-gated proposals |
| managed | reserved for a later operator-gated work slice |

## safety rules

- The latest runtime/user instruction outranks retrieved memory.
- Live context entries are not durable memory by default.
- Continuity feedback is learning evidence, not direct memory authority.
- memory promotion is review-gated unless a local policy explicitly allows narrow high-confidence direct writes.
- Public examples should use synthetic or operator-approved data only.
- No public doc should claim that ShyftR expands a hard model context limit.

## implementation surfaces

The public alpha implements:

- `live_context` cell layout with append-only live context and harvest ledgers;
- live context capture through CLI, MCP, and local HTTP service surfaces;
- bounded advisory pack assembly with item/token caps, duplicate suppression, stale-item suppression, roles, and provenance;
- session harvest through CLI, MCP, and local HTTP service surfaces;
- deterministic harvest classification reports;
- review-gated memory promotion proposals from harvest;
- continuity improvement proposal wiring from harvest;
- synthetic runtime fixtures and evaluation metrics.

External capture and pack surfaces remain dry-run unless an explicit write flag is supplied. Real-runtime profile enablement remains outside this alpha and requires operator approval.
