# ShyftR

[![CI](https://github.com/stefan-mcf/shyftr/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/stefan-mcf/shyftr/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Status: stable local](https://img.shields.io/badge/status-stable%20local--first-green)

Attachable recursive memory cells for AI agents.

ShyftR gives agents memory that can prove where it came from, whether it helped, and how it changed over time. It captures evidence in append-only cell ledgers, promotes reviewed memories through a regulator, assembles trust-labeled packs for runtimes, and records feedback so useful memory gains confidence while harmful or stale memory can be challenged.

## Current status

ShyftR is a stable local-first product line for developer-operated agent memory. The supported path is clone, install, run local cells, and use synthetic or operator-approved non-sensitive data. Hosted platform operation, multi-tenant deployment, package publication, and broad managed-memory replacement claims remain outside the current public release.

The public surface is intentionally compact: product docs, concepts, API/console references, examples, tests, and release gates are tracked; local planning, status ledgers, runbooks, research notes, and operator notes are kept out of the public clone.

## What ShyftR does

ShyftR is a local memory-cell substrate for agents and agent runtimes:

| Step | What happens |
|---|---|
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

The public release supports:

- local cell creation and append-only ledgers;
- evidence ingestion, candidate extraction, review, and memory promotion;
- sparse, deterministic vector, and qualified hybrid retrieval surfaces for local deterministic use;
- pack generation and feedback recording;
- privacy/sensitivity policy checks for pack and provider paths;
- local diagnostics, readiness, hygiene, audit, sweep, challenge, proposal, backup, restore, and ledger verification workflows;
- optional localhost FastAPI service;
- React console for local service operation;
- runtime-neutral adapter examples and synthetic fixtures;
- public readiness and release gate scripts.

The public release uses synthetic examples by default. Use operator-approved non-sensitive data only after reviewing `SECURITY.md` and the out-of-scope boundaries in this README.

## What is deliberately out of scope

The current public release excludes:

- hosted platform operation;
- multi-tenant deployment;
- package publication or release tags without a separate release decision;
- broad managed memory backend replacement claims;
- benchmark claims without published methodology and reproducible scripts;
- automatic external runtime control beyond local adapter contracts;
- unreviewed sensitive, customer, employer, or regulated memory.

Future capabilities can expand after implementation evidence, tests, public updates, and review gates. Treat this repository as the stable local-first proof and operating surface for ShyftR cells.

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

## Release readiness gate

Before asking others to depend on a clone, run the public release gate:

```bash
bash scripts/release_gate.sh
```

Expected final line:

```text
SHYFTR_RELEASE_READY
```

The gate uses synthetic data by default. It checks CLI import/help, Python tests, deterministic local lifecycle, synthetic replacement-readiness replay, diagnostics, public readiness posture, and optional console build/audit when npm is available.

If the gate fails on a machine, capture the full terminal output, OS, Python version, Node/npm version if relevant, and whether the failure happened before or after dependency installation.

## Quickstart

The fastest proof is the deterministic local lifecycle:

```bash
bash examples/run-local-lifecycle.sh
```

The script creates a temporary cell, ingests `examples/evidence.md`, extracts a candidate, reviews it, promotes a memory, assembles a pack, records feedback, runs local diagnostics, verifies ledger heads, and creates a local backup.

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

Use throwaway cells for experiments. Do not point tests at production memory ledgers.

## Safety model

- cell ledgers are canonical truth.
- The regulator controls admission, promotion, retrieval, mutation, sensitivity, and export.
- The grid is rebuildable acceleration.
- Packs are bounded context bundles for a task/runtime.
- feedback drives confidence and review-gated proposals.
- Sensitive or regulated data requires explicit operator approval before use.
- Hosted or multi-tenant deployments require a separate deployment and security review.

See `SECURITY.md` and `docs/concepts/storage-retrieval-learning.md` for the detailed release scope.

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
| reviewed memories retain provenance back to evidence       |
+------------------------------------------------------------+
      |
      v
   pack -> runtime use -> feedback -> confidence/proposals
```

## Documentation

- `docs/development.md` — local development and verification commands.
- `docs/api.md` — optional local HTTP API reference.
- `docs/api-versioning.md` — stable `/v1` API compatibility contract.
- `docs/console.md` — local console guide.
- `docs/concepts/cells.md` — cell model and boundaries.
- `docs/concepts/storage-retrieval-learning.md` — ledger/grid/pack/feedback model.
- `docs/concepts/implementation-guardrails.md` — implementation and public/private boundaries.
- `docs/runtime-integration-example.md` — runtime-neutral adapter example.
- `docs/skills.md` — project-bundled Hermes skill for ShyftR operators.
- `docs/future-work.md` — public future-work notes.
- `examples/README.md` — runnable synthetic examples.

## Development checks

```bash
python -m compileall -q src scripts examples
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
bash scripts/release_gate.sh
```

## License

MIT. See `LICENSE`.
