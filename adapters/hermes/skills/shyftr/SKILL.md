---
name: shyftr
description: "Use when working with ShyftR: repo navigation, cells, packs, feedback, carry/continuity, live context, verification gates, public/private boundaries, or Hermes/MCP integration."
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [shyftr, memory, cells, carry, live-context, mcp, verification]
metadata:
  hermes:
    tags: [shyftr, memory, cells, carry, live-context, mcp, verification]
    related_skills: [hermes-agent, hermes-agent-skill-authoring, skill-smith]
---

# ShyftR

## Overview

ShyftR is a local-first, ledger-backed memory-cell substrate for AI agents and agent runtimes. Use the repository root as the working directory for repo-local commands.

Use this skill as a compact operating guide, not as a duplicate of the repository documentation. Repo files are operational truth. Inspect the current checkout before making capability, release, or future-work claims.

This skill covers ShyftR repo work, Hermes integration, MCP/CLI surfaces, cells, packs, feedback, carry/continuity, live context, public/private boundaries, and verification.

## When to Use

Use when:
- working in a ShyftR checkout;
- answering ShyftR capability, release, architecture, or current-status questions;
- editing ShyftR docs, status artifacts, examples, tests, MCP, CLI, provider, cells, packs, feedback, carry/continuity, or live context logic;
- using ShyftR MCP tools from Hermes;
- writing or syncing the project-bundled ShyftR Hermes skill;
- preparing public commits, pushes, status reports, or release-gate evidence.

Do not use for:
- non-ShyftR projects;
- private-core experiments unless the user explicitly routes work there;
- active queue/task state; inspect repo files, ledgers, logs, or session recall instead;
- broad memory writes without durable value.

## Repo Navigation Map

Before acting, choose the current source file for the question:

| Need | Read first |
|---|---|
| Product overview/current claim posture | `README.md`, `docs/future-work.md` |
| Cell model | `docs/concepts/cells.md` |
| Ledger/grid/pack/feedback | `docs/concepts/storage-retrieval-learning.md` |
| Public/private and implementation guardrails | `docs/concepts/implementation-guardrails.md`, `SECURITY.md` |
| Runtime contracts | `docs/concepts/runtime-integration-contract.md` |
| Carry/continuity | `docs/concepts/runtime-continuity-provider.md`, `src/shyftr/continuity.py` |
| Live context/session harvest | `docs/concepts/live-context-optimization-and-session-harvest.md`, `src/shyftr/live_context.py` |
| MCP tools | `docs/mcp.md`, `src/shyftr/mcp_server.py` |
| CLI commands | `src/shyftr/cli.py`, `docs/runtime-context-optimization-example.md` |
| Implementation evidence | `README.md`, tests, and release gates |
| Future work | `docs/future-work.md`; local-only planning/status artifacts are intentionally ignored |
| Skill packaging | `adapters/hermes/skills/shyftr/SKILL.md`, `docs/skills.md` |

Rule: if a claim can be verified from the repo, verify it from the repo. Do not rely on memory for operational state. For capability/status questions, inspect `README.md` and tracked public docs first; for command syntax, inspect `src/shyftr/cli.py` or live `--help` output before pasting commands.

## Core Model

A cell is a bounded, attachable memory unit with its own ledger, regulator, grid, packs, feedback, policy, and reports.

Lifecycle:

```text
evidence -> candidate -> memory -> pattern -> rule
```

Golden rule:

```text
cell ledgers are truth.
The grid is acceleration.
The pack is application.
feedback is learning.
memory confidence is evolution.
```

Runtime loop:

```text
ingest evidence -> request pack -> apply guidance -> record feedback -> review proposals
```

Safety rule:

```text
ShyftR proposes. The runtime applies.
```

User-facing prose should prefer `ShyftR`, `memory`, `memory_id`, `pack`, and `feedback`. Legacy aliases belong only in compatibility docs, compatibility fields, or quoted existing artifacts.

## Cell Roles

Use the right cell for the job:

```text
runtime session
  -> live context cell       high-churn working context during the session
  -> carry/continuity cell   context-pressure, continuity packs, feedback, proposals
  -> memory cell             reviewed durable memory
```

Memory cell:
- reviewed durable memory only;
- stable preferences, conventions, reusable workflows, tool quirks, recovery patterns, and rules;
- receives policy-approved direct durable memories or review-gated candidates/proposals;
- should not become a dump for active task state, queue state, branch state, or completion logs.

Carry/continuity cell:
- operator-facing alias is `carry`; formal compatibility term is `continuity`;
- supports context-pressure and compaction events;
- builds bounded packs from memory-cell context;
- records resumed-work feedback: useful, ignored, harmful, missing, stale, and promotion notes;
- should not directly mutate durable memory; it writes feedback and proposals;
- current public-safe modes are `off`, `shadow`, and `advisory`; stronger authority/managed modes remain gated unless current repo files say otherwise.

Live context cell:
- working buffer for active session state;
- captures active goal, plan, files/artifacts, constraints, decisions, failures, recoveries, verification evidence, and open questions;
- not durable memory by default;
- session harvest buckets: discard, archive, continuity feedback, memory candidate, direct durable memory, skill proposal;
- runtime adapters should trigger harvest on session close/switch, resume, reset, compression rollover, and shutdown paths where supported;
- direct durable memory should remain disabled unless an explicit reviewed local policy enables it.

Safe public frame:

```text
ShyftR captures live working context into cells, harvests durable lessons at session close, and retrieves bounded packs so agent runtimes can continue work with a leaner active prompt.
```

Avoid numeric context-window expansion claims. ShyftR can reduce prompt bloat and improve continuity, but it does not increase a provider's hard context limit.

## Hermes and MCP Tool Map

General memory tools:
- `shyftr_pack`: request bounded trust-labeled memory context.
- `shyftr_remember`: preview/write durable memory; dry-run unless `write=true`.
- `shyftr_search`: search a cell.
- `shyftr_profile`: compact profile projection.
- `shyftr_record_feedback`: record pack outcome; dry-run unless `write=true`.

Carry/continuity tools:
- `shyftr_carry_pack`
- `shyftr_carry_feedback`
- `shyftr_carry_status`
- `shyftr_continuity_pack` compatibility alias
- `shyftr_continuity_feedback` compatibility alias
- `shyftr_continuity_status` compatibility alias

Live context tools:
- `shyftr_live_context_capture`
- `shyftr_live_context_pack`
- `shyftr_session_harvest`
- `shyftr_live_context_status`

Tool discipline:
- use `write=false`/dry-run or omit `--write` first unless the user explicitly asks to write;
- use `write=true`/`--write` only after the statement, payload, and target cell are reviewed or clearly authorized;
- direct durable-memory writes from harvest require explicit local policy; otherwise produce review-gated proposals;
- do not store operational task state as durable memory;
- report user-facing results as ShyftR memory records with `memory_id` where applicable.

## CLI Snippets

Core verification from repo root:

```bash
cd <shyftr-repo>
PYTHONPATH=.:src python -m compileall -q src scripts examples
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
git status --short
```

Carry examples:

```bash
shyftr carry pack <memory_cell> <carry_cell> "query" --runtime-id local-agent --session-id s1 --compaction-id c1 --mode advisory --max-items 8 --max-tokens 1200
shyftr carry feedback <carry_cell> <carry_pack_id> resumed_successfully --runtime-id local-agent --session-id s1 --compaction-id c1 --missing-note "..."
shyftr carry status <carry_cell>
# Add --write only after reviewing the target cell and payload.
```

Live context examples:

```bash
shyftr live-context capture <live_cell> "current plan..." --runtime-id local-agent --session-id s1 --kind active_plan
shyftr live-context pack <live_cell> "what matters next" --runtime-id local-agent --session-id s1 --max-items 8 --max-tokens 1200
shyftr live-context harvest <live_cell> <carry_cell> <memory_cell> --runtime-id local-agent --session-id s1
shyftr live-context status <live_cell>
# Add --write only after review; add --allow-direct-durable-memory only under explicit local policy.
```

For full examples, inspect the repo docs and current CLI help instead of expanding this skill.

## Public/Private Boundary

Public repo may include:
- local-first contracts and implementation;
- synthetic fixtures and examples;
- public proof/status docs;
- deterministic tests and gates;
- project-bundled Hermes skill source;
- docs for CLI/MCP/HTTP surfaces.

Keep private unless explicitly approved:
- private-core ranking, scoring, or compaction heuristics;
- real memory data, customer/employer/regulated data, or personal ledgers;
- hosted, multi-tenant, or production service claims;
- commercial strategy and private operator workflows;
- Hermes-profile-specific adapter secrets or local tokens;
- direct durable-memory auto-write policy beyond reviewed public defaults.

Before public commits, classify each changed file as public proof, public contract, public synthetic example, private core, private operator material, or generated/runtime artifact. Commit only public-safe files.

## Skill Sync Rule

The repo-bundled skill is canonical and inspectable:

```text
adapters/hermes/skills/shyftr/SKILL.md
```

The local runtime copy should match it unless a clearly marked local-only note is approved:

```text
<local-hermes-skills>/software-development/shyftr/SKILL.md
```

If either copy changes, sync the other before verification and public commit. ShyftR installation should not silently mutate `~/.hermes`; operators may inspect and copy/sync the skill explicitly.

## Common Pitfalls

1. Skill duplicates repo docs: keep this skill compact and route to repo files instead of copying long doctrine.
2. Capability overclaiming: current claims must match tracked public docs, tests, and release gates.
3. Context-window overclaiming: ShyftR reduces prompt bloat and improves continuity; it does not increase hard provider limits.
4. Carry naming drift: use `carry` for operator-facing CLI/MCP/HTTP; preserve `continuity_*` compatibility aliases, fields, and ledger paths unless a reviewed migration says otherwise.
5. Live context pollution: active session state is not durable memory by default; harvest must classify it.
6. Dry-run defaults: external MCP/HTTP/CLI write surfaces often require explicit `write=true` or `--write` after review.
7. Legacy vocabulary leakage: new prose should use evidence/candidate/memory/pattern/rule, pack, feedback, and `memory_id`; legacy aliases only in compatibility notes or raw field references.
8. Public/private leakage: do not commit private-core heuristics, real data, local Hermes profile secrets, or private operator material.
9. Scope invention: read tracked public docs and local-only planning/status artifacts before naming or extending work scopes.
10. Self-referential SHA drift: separate preflight/tested SHA from final artifact commit SHA in closeouts.
11. Operational-memory drift: do not store ShyftR queue state, branch/worktree state, worker summaries, artifact paths, or completion logs in Hermes-main memory; inspect files/ledgers/session recall instead.

## Verification Checklist

- [ ] Current repo files inspected before capability, release, or future-work claims.
- [ ] Cell role selected correctly: memory, carry/continuity, or live context.
- [ ] Writes are dry-run/proposal-first unless explicit approval exists.
- [ ] Public/private classification complete for changed files.
- [ ] Current vocabulary preserved; legacy terms appear only for compatibility.
- [ ] No numeric context-window expansion claim.
- [ ] Relevant tests/gates run and outputs inspected.
- [ ] Project-bundled skill and local Hermes skill are synced when skill content changes.
- [ ] For CLI snippets or MCP/tool claims, current help/schema/source was checked.
