# ShyftR

Local-first, append-only memory control plane for AI agents.

## Current status

ShyftR is a local-first alpha / controlled-pilot developer-preview MVP. It is designed for local Cells, synthetic demos, and operator-approved pilots where durable agent memory must stay inspectable, review-gated, and file-backed.

It is not a hosted SaaS product, not a multi-tenant production service, not production-hardened, and not a package release.

## Why it exists

Agent memory often becomes opaque profile state, ad hoc context, or a vector index without durable evidence. ShyftR gives an agent a local memory Cell whose ledger is the source of truth:

- Pulses capture raw experience as append-only evidence.
- Sparks are extracted lessons awaiting review.
- Charges are reviewed durable memory.
- Packs supply bounded context to a runtime.
- Signals report whether that context helped or harmed future work.

## What works today

- Local Cell creation and append-only ledgers.
- Pulse ingestion, Spark extraction, review, and Charge promotion.
- Sparse, deterministic vector, and hybrid retrieval surfaces.
- Pack generation and Signal recording.
- Hygiene, readiness, diagnostics, audit, sweep, challenge, proposal, privacy, and backup/restore workflows.
- Optional localhost FastAPI service and React console.
- Runtime-neutral adapter examples and synthetic demo fixtures.

See `docs/status/current-implementation-status.md` for the evidence-backed capability matrix.

## What is deliberately out of scope

- Hosted platform operation.
- Multi-tenant production deployment.
- Package publishing or release tags without a separate release decision.
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

The script creates a temporary Cell, ingests `examples/pulse.md`, extracts and reviews a Spark, promotes a Charge, assembles a Pack, records a Signal, runs local diagnostics, verifies ledger heads, and creates a local backup.

Manual path:

```bash
shyftr init-cell /tmp/shyftr-demo-cell --cell-id demo-cell
shyftr ingest /tmp/shyftr-demo-cell examples/pulse.md --kind lesson
shyftr spark /tmp/shyftr-demo-cell <source_id>
shyftr approve /tmp/shyftr-demo-cell <spark_id> --reviewer demo --rationale "Bounded synthetic lesson."
shyftr charge /tmp/shyftr-demo-cell <spark_id> --promoter demo
shyftr pack /tmp/shyftr-demo-cell "Pack relevance" --task-id demo-task
shyftr signal /tmp/shyftr-demo-cell <pack_id> success --useful <charge_id>
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
Pulse -> Spark -> Charge -> Pack -> Signal
          review gate       bounded use    feedback
```

- Cell ledgers are canonical truth.
- Grid/index/API/UI/profile artifacts are projections or append-only writers.
- The Regulator boundary controls promotion, retrieval, sensitivity, and export decisions.
- Backups and ledger-head verification make local state auditable.
- Review and proposal flows are explicit; ShyftR does not silently rewrite durable memory.

## Architecture

```text
External runtime or CLI
        |
        v
   Pulse ingestion  ---> append-only Cell ledger
        |                         |
        v                         v
 Spark extraction --review--> Charge promotion
        |                         |
        +-------- Grid / retrieval projections
                                  |
                                  v
                           Pack supplied to agent
                                  |
                                  v
                           Signal updates confidence
```

## Documentation

- `docs/status/current-implementation-status.md` — evidence-backed capability matrix.
- `docs/status/alpha-readiness.md` — public alpha scope, tester data boundaries, and alpha gate.
- `docs/status/public-readiness-audit.md` — public-prep finding ledger and publication gate.
- `docs/development.md` — setup and local verification.
- `docs/demo.md` — CLI demo flow.
- `docs/demo-runtime-integration.md` — runtime adapter demo.
- `docs/api.md` — localhost service endpoints.
- `docs/console.md` — React console setup and boundaries.
- `docs/concepts/` — concept and architecture notes.
- `examples/README.md` — synthetic examples and lifecycle script.

Historical plans, sources, feeds, and runbooks remain under `docs/` as implementation notes. Treat them as historical or future-planning material unless a status document marks a capability current.

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
