# ShyftR live context optimization and session harvest concept

Date: 2026-05-07
Status: source research note
Scope: runtime-neutral concept; not an implementation claim by itself

## summary

ShyftR can support a runtime's context-management loop without claiming to expand a model's hard context limit. The useful product frame is context optimization: capture live working context into cells, keep the active prompt lean, and return bounded packs when the runtime needs continuity.

The concept should avoid numeric context-window claims. The safe claim is:

```text
ShyftR helps agent runtimes work longer with less prompt bloat by moving useful live context into cells, then retrieving bounded context packs when needed.
```

This extends the existing runtime continuity provider direction. The continuity provider helps a runtime-owned mechanical compactor. A broader context-optimization layer adds live context capture and session-close harvest so the prompt does not become the only place useful context can live.

## problem

Long-running agent sessions accumulate many kinds of context:

- current task intent;
- active files, artifacts, and references;
- operator preferences;
- project constraints;
- recent decisions;
- failed attempts and recoveries;
- verification evidence;
- open questions;
- compaction events and continuity feedback.

A runtime can keep all of this in the prompt until the model approaches context pressure, but that creates prompt bloat and makes compaction more lossy. A mechanical compactor can summarize the visible transcript, but it does not by itself know which context deserves durable memory, which context is only useful for the current session, and which context should be retained as evidence for future continuity learning.

ShyftR's cell model can separate these responsibilities.

## recommended cell roles

Use three related but separate cell roles.

```text
live context cell
  captures working state during a session

continuity cell
  records context-management events, continuity packs, feedback, and proposals

memory cell
  stores reviewed durable memory for future work
```

### live context cell

The live context cell is a working buffer for high-churn session material. It should capture useful context while the runtime works, but it should not become long-term memory by default.

Typical entries:

- active goal;
- current plan or checklist;
- active files or artifacts;
- recent decisions;
- current constraints;
- failed attempts;
- verification results;
- unresolved blockers;
- material likely to help within this session.

Expected lifecycle:

```text
session starts
-> live context cell opens
-> runtime appends context-worthy entries
-> runtime requests bounded packs when needed
-> session close harvest classifies entries
-> live context cell is closed, expired, or compacted
```

The live context cell should be bounded by retention policy and should have an explicit closeout. It is a context source, not a permanent prompt.

### continuity cell

The continuity cell is the evidence record for context management itself. It records how well ShyftR and the runtime preserved continuity.

Typical entries:

- context-pressure events;
- continuity pack requests;
- continuity packs;
- pack item selections and suppressions;
- compaction feedback;
- missing-memory notes;
- stale-memory notes;
- promotion proposals;
- synthetic evaluation reports;
- pack budget and mode decisions.

The continuity cell should not directly mutate durable memory. It can emit review-gated proposals into the memory lifecycle.

### memory cell

The memory cell is the durable reviewed store. It receives only material that should remain useful beyond the session.

Typical entries:

- stable user preferences;
- durable project conventions;
- reusable workflows;
- tool quirks;
- verified failure and recovery patterns;
- rules or patterns promoted after review.

The memory cell should not receive the whole live context cell at closeout. It should receive approved or high-confidence memory items only.

## session-close harvest

Session-close harvest is the bridge between live context and durable memory.

At close, ShyftR should classify live context entries into buckets:

| Bucket | Destination | Meaning |
| --- | --- | --- |
| discard | none or temporary audit only | noise that no longer helps |
| archive | session archive or live-cell closeout ledger | useful for reconstruction but not future prompt injection |
| continuity feedback | continuity cell | evidence about pack quality, compaction loss, stale items, or missing memory |
| memory candidate | memory cell candidate ledger | possibly durable, review needed |
| direct durable memory | memory cell | safe high-confidence durable fact, if the operator policy allows direct promotion |
| skill proposal | skill/update proposal surface | reusable procedure better stored as documentation or a skill |

The harvest should be idempotent. Re-running it for the same session should not duplicate evidence or promotion proposals.

Recommended flow:

```text
runtime session closes
-> ShyftR reads live context cell and continuity evidence
-> harvest classifier groups entries
-> ShyftR writes closeout evidence
-> ShyftR writes memory promotion proposals
-> ShyftR writes continuity improvement proposals
-> ShyftR marks the live context cell closed
```

## prompt-bloat control

The key rule is:

```text
the prompt should stay lean.
the cells may grow.
the pack must stay bounded.
```

ShyftR should never dump an entire cell into the prompt. It should assemble bounded packs based on task relevance, trust, confidence, recency, and feedback.

Pack construction should account for:

- current task query;
- runtime mode: off, shadow, advisory, or future operator-gated authority;
- maximum item count;
- token budget;
- duplicate suppression against the live prompt;
- stale or superseded memory caution;
- provenance and trust labels;
- explicit exclusions.

## relationship to the runtime compactor

The runtime still owns mechanical context operations:

- trimming;
- summarizing;
- preserving recent turns;
- protecting tool-call pairs;
- preserving active task state;
- building the final model prompt.

ShyftR supplies context intelligence around those operations:

- pre-compaction continuity packs;
- live context packs during normal turns;
- post-compaction feedback;
- session-close harvest;
- memory promotion proposals;
- pack tuning proposals.

This keeps ShyftR runtime-neutral and avoids claiming that ShyftR replaces the compactor.

## modes

The existing continuity modes can extend naturally to live context optimization.

| Mode | Live context behavior | Continuity behavior | Memory behavior |
| --- | --- | --- | --- |
| off | no capture | no continuity pack | no promotion |
| shadow | capture and classify only | log would-have-selected packs | propose only, no write to memory |
| advisory | return bounded packs | record feedback and proposals | write only policy-allowed direct memories or proposals |
| managed | future gate | stronger pack obligations in bounded domains | review-gated or policy-approved promotion |

Public alpha should stop at shadow and advisory unless a later operator gate opens managed behavior.

## success criteria

A context-optimization implementation is useful when it proves:

- active prompts get smaller or less repetitive;
- important context remains recoverable through packs;
- session closeout does not lose durable lessons;
- memory cell quality does not degrade through noisy promotion;
- continuity feedback improves later pack selection;
- the runtime's latest user instruction remains more authoritative than retrieved memory;
- all writes remain inspectable through append-only ledgers.

## risks and mitigations

| Risk | Mitigation |
| --- | --- |
| live context becomes a second bloated prompt | hard pack budgets and no bulk injection |
| stale context is retrieved as if current | recency, supersession, and caution roles |
| noisy session state pollutes memory | harvest buckets and review-gated promotion |
| useful context is lost on crash | optional incremental writes for high-value live context plus idempotent harvest |
| continuity cell grows without learning | closeout metrics and proposal generation |
| runtime treats advisory pack as instruction | explicit advisory labels and latest-instruction priority |
| private runtime details leak into public docs | synthetic examples and runtime-neutral contracts only |

## recommended product wording

Use:

```text
ShyftR is a context optimizer for agent runtimes: it captures live working context into cells, harvests durable lessons at session close, and retrieves bounded context packs so work can continue with a leaner active prompt.
```

Avoid:

```text
ShyftR increases the model context window.
ShyftR turns one token limit into another.
ShyftR provides infinite context.
ShyftR replaces the runtime compactor.
```

## recommended next plan

The next implementation plan should add context optimization as a layer after the runtime continuity provider alpha:

1. formalize the live context cell role;
2. add live context capture ledgers and schema;
3. add bounded live context pack assembly;
4. add session-close harvest and flush;
5. connect harvest to continuity feedback and memory proposals;
6. add synthetic runtime fixtures;
7. add metrics for prompt-bloat reduction, pack usefulness, and memory promotion quality;
8. keep real runtime activation and managed behavior operator-gated.
