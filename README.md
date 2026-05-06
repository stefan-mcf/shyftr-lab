# ShyftR

[![CI](https://github.com/stefan-mcf/shyftr/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/stefan-mcf/shyftr/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Status: alpha](https://img.shields.io/badge/status-local--first%20alpha-orange)

Attachable recursive memory cells for AI agents.

ShyftR gives agents memory that can prove where it came from, whether it helped, and how it changed over time. It captures evidence in append-only cell ledgers, promotes reviewed memories through a regulator, assembles trust-labeled packs for runtimes, and records feedback so useful memory gains confidence while harmful or stale memory can be challenged.

## Current status

ShyftR is a local-first alpha / controlled-pilot developer preview. The supported public path is to clone the repository, install it in a Python 3.11+ environment, run synthetic local examples, inspect the ledgers, and run the alpha gate before using any operator-approved pilot data.

See `docs/status/current-implementation-status.md` for the evidence-backed capability matrix.

## What ShyftR does

ShyftR is a local memory-cell substrate for agents and agent runtimes:

| Step | What happens |
|---|---|---|
| evidence | raw task output, notes, logs, or example material enter an append-only cell ledger |
| candidate | ShyftR extracts bounded memory proposals from evidence |
| memory | a reviewer approves a candidate before it becomes durable memory |
| pack | the regulator assembles a bounded, trust-labeled context bundle for a runtime |
| feedback | the runtime reports whether the pack helped, harmed, or missed something |
| confidence | useful memory can gain confidence; harmful, stale, or contradictory memory can be challenged |
| pattern and rule | recurring memories can be distilled into higher-order guidance under review gates | 

The result is agent memory that stays inspectable. Durable learning remains tied to evidence, review, provenance, and feedback instead of disappearing into opaque profile state.

## Why it matters

Long-running agents need more than retrieved snippets. They need memory that can answer operational questions:

- Where did this memory come from?
- Who or what reviewed it before durable use?
- Which task received it in a pack?
- Did it help, harm, or fail to apply?
- Should confidence rise, decay, or trigger a challenge?
- Which material is raw evidence, unreviewed candidate, reviewed memory, emerging pattern, or shared rule?

ShyftR treats memory as an auditable learning loop. A first run can create evidence. Review can promote memory. A later run can receive a pack. feedback from that run can update confidence and produce review-gated proposals.

## What makes ShyftR different

| Need | Typical solution category | ShyftR stance |
|---|---|---|
| Store facts | profile stores or framework memory helpers | preserve provenance and require review before durable authority |
| Search context | vector index or RAG pipeline | keep cell ledgers as truth and use indexes as rebuildable acceleration |
| Scope memory | global assistant profile | attach cells to agents, users, projects, teams, applications, or domains |
| Use memory safely | raw retrieval into prompt context | assemble trust-labeled packs through regulator policy |
| Improve over time | manual edits or opaque updates | record feedback and evolve confidence from verified results |

ShyftR is strongest when the memory itself must be portable, local-first, evidence-backed, review-gated, and feedback-aware.

## Why cells

A cell is an isolated, attachable, durable memory namespace. It can attach to a person, assistant, agent, project, team, application, domain, capability, or shared rule layer.

Each cell has:

- an append-only ledger as canonical truth;
- a regulator for admission, review, retrieval, sensitivity, and export controls;
- reviewed memories with provenance back to evidence;
- rebuildable grid indexes for retrieval acceleration;
- packs that expose bounded context to a runtime;
- feedback records that show whether retrieved memory helped;
- reports, diagnostics, and backups for local inspection.

Cells let different scopes learn without collapsing everything into one global profile. They also make it possible to export, audit, back up, or discard a memory scope deliberately.

## What works today

The public alpha currently supports:

- local cell creation and append-only ledgers;
- evidence ingestion, candidate extraction, review, and memory promotion;
- sparse, deterministic vector, and qualified hybrid retrieval surfaces for local deterministic use;
- pack generation and feedback recording;
- privacy/sensitivity policy checks for pack and provider paths;
- local diagnostics, readiness, hygiene, audit, sweep, challenge, proposal, backup, restore, and ledger verification workflows;
- optional localhost FastAPI service;
- React console developer preview backed by the local service;
- runtime-neutral adapter examples and synthetic fixtures;
- public readiness and alpha gate scripts.

The public alpha uses synthetic examples by default. Use operator-approved non-sensitive data only after reviewing `SECURITY.md` and `docs/status/alpha-readiness.md`.

## What is deliberately out of scope

The current public release excludes:

- hosted platform operation;
- multi-tenant production deployment;
- package publishing or release tags without a separate release decision;
- broad managed memory backend replacement claims;
- benchmark claims without published methodology and reproducible scripts;
- automatic external runtime control beyond local adapter contracts;
- unreviewed sensitive, customer, employer, or regulated memory.

Future capabilities can expand after implementation evidence, tests, public status updates, and review gates. Until then, treat this repository as a local-first alpha proof surface.

## Install from clone

```bash
git clone https://github.com/stefan-mcf/shyftr.git
cd shyftr
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev,service]'
shyftr --help
```

Requirements:

- Python 3.11 or newer.
- Node 20+ only if you want to build the optional console.
- No hosted account or external service is required for the local proof path.

## Alpha gate

Before asking others to test a clone, run the public alpha gate:

```bash
bash scripts/alpha_gate.sh
```

Expected final line:

```text
ALPHA_GATE_READY
```

The gate uses synthetic data only. It checks CLI import/help, Python tests, deterministic local lifecycle, synthetic replacement-readiness replay, diagnostics, public readiness posture, and optional console build/audit when npm is available.

If the gate fails on a machine, capture the full terminal output, OS, Python version, Node/npm version if relevant, and whether the failure happened before or after dependency installation.

## Quickstart

The fastest proof is the deterministic local lifecycle:

```bash
bash examples/run-local-lifecycle.sh
```

The script creates a temporary cell, ingests `examples/evidence.md`, extracts a candidate, reviews it, promotes a memory, assembles a pack, records feedback, runs local diagnostics, verifies ledger heads, and creates a local backup.

### What the demo proves

The local lifecycle demonstrates the complete learning loop with synthetic data:

1. evidence enters an append-only ledger;
2. a candidate is extracted from that evidence;
3. review happens before durable memory promotion;
4. a pack supplies bounded context for a task;
5. feedback records whether the pack was useful;
6. diagnostics, ledger verification, and backup make the cell inspectable.

### Manual CLI path

Use this after the scripted proof if you want to see each lifecycle command. Replace placeholder IDs with the IDs printed by the previous command.

```bash
shyftr init-cell /tmp/shyftr-demo-cell --cell-id demo-cell
shyftr ingest /tmp/shyftr-demo-cell examples/evidence.md --kind lesson
shyftr candidate /tmp/shyftr-demo-cell <source_id>
shyftr approve /tmp/shyftr-demo-cell <candidate_id> --reviewer demo --rationale "Bounded synthetic lesson."
shyftr memory /tmp/shyftr-demo-cell <candidate_id> --promoter demo
shyftr pack /tmp/shyftr-demo-cell "pack relevance" --task-id demo-task
shyftr feedback /tmp/shyftr-demo-cell <pack_id> success --useful <memory_id>
```

Use throwaway cells for experiments. Do not point alpha tests at production memory ledgers.

## Example lifecycle

A typical agent-memory loop looks like this:

```text
First run:
  agent or runtime -> evidence -> append-only cell ledger

Review:
  evidence -> candidate -> approved memory

Next run:
  task query -> regulator -> trust-labeled pack -> agent or runtime

Closeout:
  result -> feedback -> confidence update -> review-gated proposals
```

Durable promotion and runtime application are separate loops:

```text
Durable lifecycle:
evidence -> candidate -> memory -> pattern -> rule

Application loop:
pack -> feedback -> confidence
```

Pattern and rule distillation are future-facing unless the README cites narrow tested local behavior. The alpha's reliable public claim is local evidence capture, review-gated memory promotion, pack generation, feedback recording, and inspectable ledger-backed operation.

## Architecture

```text
agent or runtime
      |
      v
  evidence intake
      |
      v
+--------------------------- cell ---------------------------+
| append-only ledger is truth                                |
| regulator gates admission, review, retrieval, and export   |
| grid indexes are rebuildable acceleration                  |
| reviewed memory, patterns, and rules carry provenance      |
+------------------------------------------------------------+
      |
      v
trust-labeled pack -> agent run -> feedback -> confidence
```

### Trust tiers in a pack

| Tier | Meaning | How to treat it |
|---|---|---|
| rule | highest-confidence shared guidance after explicit review | apply when in scope |
| memory | reviewed durable memory with provenance | use as primary guidance or caution |
| pattern | recurring structure distilled from related memories | treat as emerging guidance unless fully promoted |
| candidate | proposed memory awaiting review | background only unless approved |
| evidence | raw source material | inspect for provenance, never treat as durable authority |

### Pack roles

A pack separates memory by role so a runtime can use guidance without losing warnings:

- `guidance_items` — action-oriented memories, rules, or patterns;
- `caution_items` — failure signatures, anti-patterns, supersession warnings, or other negative-space memory;
- `background_items` — supporting patterns, candidates, or evidence for interpretation;
- `conflict_items` — contradictory material requiring review before confident use.

Every pack item carries trust tier, kind, confidence, score, and provenance where available.

### Regulator responsibilities

The regulator is the operational policy surface around a cell. It controls:

- admission checks before evidence can support learning;
- candidate review before memory promotion;
- sensitivity and policy filtering;
- trust-tier, token, scope, and export limits for packs;
- proposal review before higher-authority memory changes;
- quarantine or challenge paths for harmful, stale, or conflicting material.

The regulator keeps automated discovery separate from durable authority.

## Runtime integration

ShyftR attaches to external runtimes through four runtime-neutral flows:

```text
external runtime -> evidence  -> ShyftR cell
external runtime <- pack      <- ShyftR cell
external runtime -> feedback  -> ShyftR cell
external runtime <- proposals <- ShyftR cell
```

External runtimes own scheduling, execution, retries, model choice, queue state, and immediate operational policy. ShyftR owns durable memory, provenance, regulator gates, packs, feedback, confidence, and advisory proposals.

The file/JSONL adapter examples under `examples/integrations/worker-runtime/` show the contract without depending on a specific framework or hosted service. See `docs/concepts/runtime-integration-contract.md` and `docs/runtime-integration-example.md` for the detailed request and response shapes.

## Safety model

ShyftR's safety model is local-first, append-only, review-gated, and explicit about what writes durable truth.

### Safety, privacy, and trust boundaries

- Use synthetic examples by default.
- Use operator-approved non-sensitive pilot data only after reviewing `SECURITY.md`.
- Keep API keys, tokens, `.env` files, customer data, employer data, regulated data, and production memory ledgers out of alpha tests.
- cell ledgers are canonical truth.
- grid indexes, profile projections, API summaries, console views, and readiness reports are rebuildable projections or local append-only writers.
- Review gates control durable memory promotion.
- The regulator controls retrieval and export decisions.
- ShyftR does not silently rewrite durable memory.
- Hosted SaaS and multi-tenant production guarantees sit outside the current public alpha.

### What writes truth

Durable truth is written by local cell ledger operations:

- `shyftr ingest` writes evidence records;
- `shyftr approve` and `shyftr reject` write review records;
- `shyftr memory` / `shyftr promote` write promotion and memory records;
- `shyftr pack` writes bounded pack/retrieval records derived from existing ledgers;
- `shyftr feedback` writes feedback records;
- the optional local service delegates to the same local functions;
- the console is a local UI over the same lifecycle boundaries.

### What stays projection

These surfaces help retrieval, inspection, or UX, but they can be rebuilt or regenerated from ledgers:

- grid indexes;
- profile summaries;
- readiness and diagnostics reports;
- API response summaries;
- console views;
- exported proposal files and backup archives.

See `SECURITY.md`, `docs/status/alpha-readiness.md`, and `docs/concepts/storage-retrieval-learning.md` for the detailed alpha boundary.

## Local service and console

The optional service is a localhost wrapper around the same local cell functions:

```bash
shyftr serve --host 127.0.0.1 --port 8014
curl -fsS http://127.0.0.1:8014/health
```

Console developer preview:

```bash
cd apps/console
cp .env.example .env
npm install
npm run dev
npm run build
```

See `docs/api.md` and `docs/console.md` for current endpoints, UI capabilities, and localhost boundaries.

## Documentation

Start here:

- `docs/status/current-implementation-status.md` — evidence-backed capability matrix and public wording rule.
- `docs/status/alpha-readiness.md` — tester audience, alpha gate, and data boundaries.
- `docs/example-lifecycle.md` — CLI lifecycle walkthrough.
- `examples/README.md` — synthetic examples and lifecycle script.

Concepts:

- `docs/concepts/cells.md` — cell, regulator, ledger, grid, pack, and feedback concepts.
- `docs/concepts/storage-retrieval-learning.md` — storage truth, trust tiers, pack roles, and confidence loop.
- `docs/concepts/terminology-compatibility.md` — canonical vocabulary and legacy alias policy.
- `docs/concepts/runtime-integration-contract.md` — runtime-neutral adapter contract.

Reference:

- `docs/api.md` — localhost service endpoints.
- `docs/console.md` — React console setup and boundaries.
- `docs/development.md` — setup, tests, and local verification.

Governance:

- `CONTRIBUTING.md` — contribution workflow.
- `SECURITY.md` — security and sensitive-data guidance.
- `CHANGELOG.md` — public change history.
- `LICENSE` — MIT license.

Planning and source material:

- `docs/plans/` — implementation planning notes.
- `docs/sources/` — source material and decision captures.
- `docs/feeds/` — historical research or review feeds.
- `docs/runbooks/` — operational notes.

Treat planning, source, feed, and runbook files as historical or planning material unless a status document marks a capability current.

## Development checks

Run the full local verification bundle before trusting or publishing changes:

```bash
python -m pytest -q
bash examples/run-local-lifecycle.sh
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
bash scripts/check.sh
bash scripts/alpha_gate.sh
git diff --check
```

Optional console verification when Node/npm are available:

```bash
(cd apps/console && npm install && npm run build && npm audit --omit=dev)
```

For a clean install smoke:

```bash
bash scripts/smoke-install.sh
```

## Project status and future direction

The public repository proves local-first memory cells, append-only ledgers, review-gated memory promotion, pack generation, feedback recording, local service/console developer preview, and synthetic runtime-integration examples.

Broader adoption paths remain gated by implementation evidence, tests, status updates, and review. Future-facing work includes stronger pattern/rule distillation, larger-cell retrieval adapters, richer proposal review, and more complete external runtime integration patterns. Keep current-tense public claims tied to `docs/status/current-implementation-status.md`.

## Contributing

Contributions should preserve the alpha boundary, local-first behavior, synthetic test data, public/private separation, and terminology rules. Start with `CONTRIBUTING.md` and `docs/development.md`.

## Security

Report vulnerabilities and sensitive-data concerns through the process in `SECURITY.md`. Do not include secrets, customer data, private ledgers, or production memory in issues, examples, screenshots, or test fixtures.

## License

MIT. See `LICENSE`.
