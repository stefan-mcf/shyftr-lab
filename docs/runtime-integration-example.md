# Runtime Integration Demo

This example shows a runtime-neutral closed learning loop using only files and
JSON contracts. It avoids product-specific runtime details; any worker system
that can write files and call the ShyftR CLI can use the same pattern.

Fixture files live in `examples/integrations/worker-runtime/`:

- `adapter.yaml` declares how ShyftR discovers runtime evidence.
- `evidence-closeout.md` is a human-readable closeout evidence from a completed task.
- `feedback-log.jsonl` is an append-only runtime event stream.
- `task-request.json` is a pack request before work starts.
- `feedback-report.json` is a feedback report after work finishes.

## 1. Validate the adapter

```bash
shyftr adapter validate --config examples/integrations/worker-runtime/adapter.yaml
```

Validation proves the runtime can describe its evidence locations without custom
code in ShyftR.

## 2. Discover and ingest runtime evidences

```bash
shyftr adapter discover --config examples/integrations/worker-runtime/adapter.yaml --dry-run
shyftr adapter ingest --config examples/integrations/worker-runtime/adapter.yaml --cell-path ./demo-cell
```

The adapter turns the closeout evidence, feedback JSONL rows, task request, and
feedback report into append-only cell ledger evidence records. The cell ledger remains
canonical truth; adapter state and indexes are rebuildable acceleration.

## 3. Review and promote memory

The demo test exercises the evidence -> candidate -> memory path by extracting a candidate
from the closeout evidence, approving it, and promoting it into a memory. That
memory can later appear in a pack.

## 4. Request a pack before the next task

`task-request.json` demonstrates the runtime-side request shape. It asks for a
small trust-filtered pack relevant to adapter config validation and JSONL sync.
The current stable API module is `shyftr.integrations.pack_api`; the public
theme term is pack.

## 5. Report feedback after the task

`feedback-report.json` demonstrates the runtime-side report shape. It records
applied and useful memory IDs, runtime references, and verification evidence.
The current stable API module is `shyftr.integrations.feedback_api`; the public
theme term is feedback.

## 6. Closed loop

The fixture includes all four feedbacks required for a useful learning loop:

- successful workflow: a pack was applied and the task succeeded;
- repeated failure signature: multiple timeout/no-report runs;
- recovery pattern: timeout window increased after repeated evidence;
- caution: ShyftR emits reviewable evidence rather than mutating runtime policy.

The accompanying synthetic fixture demonstrates the example
end to end without any product-specific runtime dependency.

## 7. Local HTTP service (optional)

When shelling out to the CLI is impractical (e.g. a runtime that only speaks
HTTP), use the optional local service wrapper:

```bash
# Install with the optional HTTP extras
pip install shyftr[service]

# Start the service
python -m shyftr.server

# Or with custom bind address & port
python -m shyftr.server --host 127.0.0.1 --port 8014
```

### Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/validate` | POST | Validate an adapter config file |
| `/ingest` | POST | Ingest a evidence via an adapter config |
| `/pack` | POST | Request a pack/pack |
| `/feedback` | POST | Report a feedback/feedback |
| `/proposals/export` | POST | Export advisory runtime proposals |

### Example: pack request via curl

```bash
curl -X POST http://127.0.0.1:8014/pack \
  -H "Content-Type: application/json" \
  -d '{
    "cell_path_or_id": "./demo-cell",
    "query": "adapter config validation",
    "task_kind": "validation",
    "external_system": "worker-runtime",
    "external_scope": "demo"
  }'
```

### Example: feedback report via curl

```bash
curl -X POST http://127.0.0.1:8014/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "cell_path_or_id": "./demo-cell",
    "pack_id": "pack-demo-001",
    "result": "success",
    "external_system": "worker-runtime",
    "external_scope": "demo",
    "external_run_id": "run-001",
    "applied_memory_ids": ["memory-abc"],
    "useful_memory_ids": ["memory-abc"],
    "verification_evidence": {"tests": "passed"}
  }'
```

### Example: Proposal export via curl

```bash
curl -X POST http://127.0.0.1:8014/proposals/export \
  -H "Content-Type: application/json" \
  -d '{
    "cell_path": "./demo-cell",
    "external_system": "worker-runtime",
    "include_accepted": false
  }'
```
