# ShyftR Examples

All examples are synthetic and local-only. They are safe fixtures for learning the evidence -> candidate -> memory -> pack -> feedback loop without network access, API keys, or external services.

## Files

| Path | Purpose | Used by |
|---|---|---|
| `examples/evidence.md` | Synthetic evidence describing a pack relevance lesson. | `shyftr ingest`, demo lifecycle, tests. |
| `examples/task.json` | Synthetic task request for pack generation. | Documentation and JSON parse checks. |
| `examples/run-local-lifecycle.sh` | End-to-end local lifecycle using a temp cell. | README quickstart, CI smoke, `scripts/check.sh`. |
| `examples/integrations/runtime-adapter.yaml` | Runtime-neutral adapter config fixture. | Adapter validation examples. |
| `examples/integrations/task-request.json` | Runtime-neutral pack request fixture. | Integration docs/tests. |
| `examples/integrations/feedback-report.json` | Runtime-neutral feedback report fixture. | Integration docs. |
| `examples/integrations/worker-runtime/**` | Richer synthetic worker-runtime fixture. | Runtime integration docs. |

## Run the local lifecycle

```bash
python -m pip install -e '.[dev,service]'
bash examples/run-local-lifecycle.sh
```

The script creates a temporary cell under `${TMPDIR:-/tmp}`, prints its path, and leaves it in place for inspection. Remove that path when you are done.
