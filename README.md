# ShyftR

Local-first, append-only memory control plane for AI agents.

## Why it exists

Agent memory often becomes opaque profile state, ad hoc context, or a vector index without durable evidence. ShyftR gives an agent a local memory cell whose ledger is the source of truth:

- evidence captures raw experience in an append-only ledger.
- candidates are extracted lessons awaiting review.
- memories are reviewed durable memory.
- packs supply bounded context to a runtime.
- feedback reports whether that context helped or harmed future work.

## What works today

- Local cell creation and append-only ledgers.
- evidence ingestion, candidate extraction, review, and memory promotion.
- Sparse, deterministic vector, and hybrid retrieval surfaces.
- pack generation and feedback recording.
- Hygiene, readiness, diagnostics, audit, sweep, challenge, proposal, privacy, and backup/restore workflows.
- Optional localhost FastAPI service and React console.
- Runtime-neutral adapter examples and synthetic fixtures.

See `docs/status/current-implementation-status.md` for the evidence-backed capability matrix.

## What is deliberately out of scope

- Hosted platform operation.
- Multi-tenant production deployment.
- package publishing or release tags without a separate release decision.
- Distributed intelligence, federation, or network effects.
- Automatic external runtime control beyond local adapter contracts.

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

## Alpha gate

Before asking others to test a clone, run the public alpha gate:

```bash
bash scripts/alpha_gate.sh
```

Expected final line:

```text
ALPHA_GATE_READY
```

The gate uses synthetic data only and checks the CLI, tests, local lifecycle, replacement-readiness replay, diagnostics, public readiness posture, and optional console build/audit. See `docs/status/alpha-readiness.md` for tester scope and data boundaries.

## Quickstart

Run the deterministic local lifecycle:

```bash
bash examples/run-local-lifecycle.sh
```

The script creates a temporary cell, ingests `examples/evidence.md`, extracts and reviews a candidate, promotes a memory, assembles a pack, records a feedback, runs local diagnostics, verifies ledger heads, and creates a local backup.

Manual path:

```bash
shyftr init-cell /tmp/shyftr-demo-cell --cell-id demo-cell
shyftr ingest /tmp/shyftr-demo-cell examples/evidence.md --kind lesson
shyftr candidate /tmp/shyftr-demo-cell <source_id>
shyftr approve /tmp/shyftr-demo-cell <candidate_id> --reviewer demo --rationale "Bounded synthetic lesson."
shyftr memory /tmp/shyftr-demo-cell <candidate_id> --promoter demo
shyftr pack /tmp/shyftr-demo-cell "pack relevance" --task-id demo-task
shyftr feedback /tmp/shyftr-demo-cell <pack_id> success --useful <memory_id>
```

## Local service and console

```bash
shyftr serve --host 127.0.0.1 --port 8014
curl -fsS http://127.0.0.1:8014/health
```

Console:

```bash
cd apps/console
cp .env.example .env
npm install
npm run dev
npm run build
```

See `docs/api.md` and `docs/console.md` for current endpoints, UI capabilities, and localhost boundaries.

## Safety model

```text
evidence -> candidate -> memory -> pack -> feedback
          review gate       bounded use    feedback
```

- cell ledgers are canonical truth.
- grid/index/API/UI/profile artifacts are projections or append-only writers.
- The regulator boundary controls promotion, retrieval, sensitivity, and export decisions.
- Backups and ledger-head verification make local state auditable.
- Review and proposal flows are explicit; ShyftR does not silently rewrite durable memory.

## Architecture

```text
External runtime or CLI
        |
        v
   evidence ingestion  ---> append-only cell ledger
        |                         |
        v                         v
 candidate extraction --review--> memory promotion
        |                         |
        +-------- grid / retrieval projections
                                  |
                                  v
                           pack supplied to agent
                                  |
                                  v
                           feedback updates confidence
```

## Documentation

- `docs/status/current-implementation-status.md` — evidence-backed capability matrix.
- `docs/status/alpha-readiness.md` — public alpha scope, tester data boundaries, and alpha gate.
- `docs/status/public-readiness-audit.md` — public-prep finding ledger and publication gate.
- `docs/development.md` — setup and local verification.
- `docs/example-lifecycle.md` — CLI lifecycle walkthrough.
- `docs/runtime-integration-example.md` — runtime adapter example.
- `docs/api.md` — localhost service endpoints.
- `docs/console.md` — React console setup and boundaries.
- `docs/concepts/` — concept and architecture notes.
- `docs/concepts/terminology-compatibility.md` — canonical terms and deprecated alias policy.
- `examples/README.md` — synthetic examples and lifecycle script.

Historical plans, sources, feeds, and runbooks remain under `docs/` as implementation notes. Treat them as historical or planning material unless a status document marks a capability current.

## Development checks

```bash
python -m pytest -q
bash examples/run-local-lifecycle.sh
(cd apps/console && npm run build && npm audit --omit=dev)
python scripts/public_readiness_check.py
bash scripts/check.sh
bash scripts/alpha_gate.sh
```

For a clean install smoke:

```bash
bash scripts/smoke-install.sh
```

## License

MIT. See `LICENSE`.
