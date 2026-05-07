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
| Implementation evidence | `README.md`, current CI/release gates, and tracked public proof artifacts; do not assume ignored local `tests/` is public evidence |
| Future work | `docs/future-work.md`; local-only planning/status artifacts are intentionally ignored |
| Skill packaging | `adapters/hermes/skills/shyftr/SKILL.md`, `docs/skills.md` |

## Code Navigation Map

Use this when the question is about where to edit or inspect implementation first:

| Need | Open first |
|---|---|
| CLI command parsing and flags | `src/shyftr/cli.py` |
| MCP tool schemas and bridge wiring | `src/shyftr/mcp_server.py` |
| Durable memory provider/search/remember flow | `src/shyftr/provider/memory.py` |
| Core record/data models (`Evidence`, `Candidate`, `Memory`, `Pack`, `Feedback`) | `src/shyftr/models.py` |
| Pack/loadout assembly and operational-state filtering | `src/shyftr/pack.py` |
| Feedback/outcome learning | `src/shyftr/feedback.py`, `src/shyftr/outcomes.py` |
| Continuity pack and compaction feedback | `src/shyftr/continuity.py` |
| Live context capture/pack/harvest | `src/shyftr/live_context.py` |
| Ledger append/read/hash-chain behavior | `src/shyftr/ledger.py` |
| Runtime/server wiring | `src/shyftr/server.py`, `src/shyftr/console_api.py` |

Rule: prefer the first file that answers the question, not a broad tree walk. Use the repo-truth workflow below for claim and command verification.

## Terminology and Claim Guardrails

Canonical public lifecycle vocabulary is:

```text
evidence -> candidate -> memory -> pattern -> rule
```

Canonical support terms in normal prose: `cell`, `ledger`, `regulator`, `grid`, `pack`, `feedback`, `confidence`, `decay`, `quarantine`.

Compatibility rule:
- new prose, examples, and operator summaries should use canonical public terms;
- legacy aliases belong only in compatibility docs, field names, old ledger/file references, deprecated CLI/API surfaces, or quoted repo artifacts;
- do not propose removing compatibility aliases without an explicit human-approved migration path.

Current-claim rule:
- treat `README.md` as canonical public-facing truth for product posture when it has been explicitly accepted;
- use concept docs and source files to answer implementation questions, but do not "correct" the README into more negative wording unless the repo's approved readiness/docs posture requires it;
- for terminology edge cases, inspect `docs/concepts/terminology-compatibility.md` and `docs/status/plain-language-rename-ledger.md` first.

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

Runtime mode posture:
- `off`: no live capture or continuity export;
- `shadow`: capture/classify only; no exported pack or durable-memory write;
- `advisory`: export bounded packs and review-gated proposals;
- `managed`/stronger authority modes: reserved or operator-gated unless current repo files explicitly say otherwise.

Safe public frame:

```text
ShyftR captures live working context into cells, harvests durable lessons at session close, and retrieves bounded packs so agent runtimes can continue work with a leaner active prompt.
```

Avoid numeric context-window expansion claims. ShyftR can reduce prompt bloat and improve continuity, but it does not increase a provider's hard context limit.

## Repo-Truth Workflow

When answering or editing:
1. start with the smallest doc/source pointer that matches the question;
2. verify public capability/posture claims from `README.md` and tracked docs;
3. verify command syntax from `src/shyftr/cli.py`, `docs/mcp.md`, or live help/source before pasting commands;
4. verify implementation claims from the current source file, not memory;
5. sync the repo-bundled skill and local runtime copy whenever this skill changes.

## Hermes and MCP Tool Map

Use the tool group that matches the job:

| Role | Primary tools | Use for | Write posture |
|---|---|---|---|
| Durable memory retrieval/application | `shyftr_pack`, `shyftr_search`, `shyftr_profile` | retrieving bounded memory context, searching a cell, projecting compact memory state | read-only by default |
| Durable memory creation/learning | `shyftr_remember`, `shyftr_record_feedback` | proposing/writing durable memory and recording whether retrieved memory helped or harmed | preview/dry-run first; write only with reviewed payload or explicit authorization |
| Context-pressure continuity | `shyftr_carry_pack`, `shyftr_carry_feedback`, `shyftr_carry_status` | resumed-work packs, continuity feedback, continuity status | use `carry` in operator-facing prose; `continuity_*` names remain compatibility aliases |
| Live session context | `shyftr_live_context_capture`, `shyftr_live_context_pack`, `shyftr_session_harvest`, `shyftr_live_context_status` | capturing working context, exporting bounded live-context packs, harvesting session-close outputs | capture/harvest are not durable-memory authority by default |

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

For a concrete public cleanup recipe, use `references/public-surface-cleanup.md` before editing `.gitignore`, public-readiness gates, or terminology scans.

Public repo may include:
- local-first contracts and implementation;
- synthetic fixtures and examples;
- public proof/status docs;
- deterministic verification gates (compile smoke, CLI smoke, lifecycle/release gates, terminology inventory, public readiness); tracked pytest suites are not required when `tests/` is intentionally local/ignored;
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
12. Ignored local test scratch: if `tests/` or `test/` is ignored for a public-surface cleanup, preserve useful local files on disk but remove tracked copies with `git rm -r --cached -f tests` and update CI/docs away from `pytest` commands that would fail in a clean public clone.
13. Ignored status/proof artifacts: some ShyftR cleanups intentionally ignore `docs/status/` and related proof paths. When a plan asks for repo-local deliverables there, verify the files on disk directly and mention if git status will hide them; do not mistake "not visible in git status" for "not created".
14. Planning tag leakage: old public tags/releases such as `v0.0.0-planning` can expose stale tracked trees even after `main` is cleaned. Inspect and delete/replace stale tags deliberately, then verify `git ls-remote --tags origin '<tag>*'` and `gh release view <tag>` return no public release/tag unless an intentional clean tag is being published.
15. Roadmap refresh drift: when updating a roadmap/planning doc from multiple research reports, treat the newest report as source of truth, diff it against the prior source and the current roadmap, and preserve any already-started phase boundary the user marks as frozen. Add newly discovered items only after that boundary; do not quietly merge them into the frozen phase.

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
