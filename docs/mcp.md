# ShyftR MCP bridge

ShyftR exposes a small stdio MCP bridge for runtimes that support MCP.

## Server command

```bash
uv run --project . --with mcp shyftr-mcp
```

Hermes registration from this checkout:

```bash
hermes mcp add shyftr --command uv --args run --project . --with mcp shyftr-mcp
hermes mcp test shyftr
```

## Tools

### `shyftr_search`

Searches reviewed memory in a cell.

Parameters:

- `cell_path`: path to a ShyftR cell.
- `query`: search text.
- `limit`: optional max result count, capped at 50.
- `trust_tiers`: optional list filter.
- `kinds`: optional list filter.

Result records use `memory_id` for user-facing identifiers.

### `shyftr_pack`

Builds a bounded pack for an agent/runtime. The tool defaults to dry-run mode, so retrieval logging is skipped unless `write` is explicitly true.

Parameters:

- `cell_path`, `query`, `task_id`.
- `runtime_id`: default `mcp`.
- `max_items`: default 10, capped at 50.
- `max_tokens`: default 2000, capped at 12000.
- `write`: default false.

### `shyftr_profile`

Builds a compact profile projection from reviewed memory. The projection is rebuildable and does not become canonical truth.

### `shyftr_remember`

Previews or writes explicit memory through ShyftR policy.

`write` defaults to false. A dry-run returns a preview and does not mutate ledgers. Re-run with `write=true` only after the statement and kind are reviewed.

### `shyftr_record_feedback`

Previews or records feedback for a pack.

`write` defaults to false. The bridge accepts user-facing `*_memory_ids` fields and maps them to the internal provider API.

## Safety boundary

The bridge is read/pack-first. Memory writes and feedback writes require `write=true`; destructive lifecycle operations are not exposed through this MCP surface.

## Verification

```bash
PYTHONPATH=src python3 -m py_compile src/shyftr/mcp_server.py
PYTHONPATH=src python3 -m py_compile src/shyftr/mcp_server.py src/shyftr/memory_provider.py src/shyftr/pack.py
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
```
