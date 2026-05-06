# ShyftR Local HTTP API

Status: stable local adapter. The HTTP service is optional and delegates to the same append-only cell functions used by the CLI. It is not a hosted product and does not create a second truth store.

## Start the service

```bash
python -m pip install -e '.[service]'
shyftr serve --host 127.0.0.1 --port 8014
curl -fsS http://127.0.0.1:8014/health
```

Use `127.0.0.1`/`localhost` for normal operation. Binding to a non-local interface is outside the local default and should be reviewed like any other deployment decision.

## Endpoint summary

| Method | Path | Purpose | Write authority |
|---|---|---|---|
| GET | `/health` | Service health check. | none |
| POST | `/validate` | Validate an adapter config. | none |
| POST | `/ingest` | Ingest adapter-discovered evidence records into a cell. | append-only evidence ledgers |
| POST | `/pack` | Request a pack from a runtime request. | retrieval/diagnostic logs may be appended |
| POST | `/feedback` | Report a feedback/feedback for a pack. | append-only feedback/feedback ledgers and counters |
| POST | `/proposals/export` | Export advisory runtime proposals. | report artifact when output path is supplied |
| GET | `/cells` | List cells under a local root. | none |
| GET | `/cell/{cell_id}/summary` | cell dashboard summary. | none |
| GET | `/cell/{cell_id}/status` | Alias-style cell status summary. | none |
| GET | `/cell/{cell_id}/memories` | memory explorer with filters. | none |
| GET | `/cell/{cell_id}/candidates` | candidate review queue. | none |
| POST | `/cell/{cell_id}/candidates/{candidate_id}/review` | Approve, reject, split, or merge a candidate. | append-only review ledgers |
| POST | `/cell/{cell_id}/memories/{memory_id}/action` | Deprecate, forget, challenge/isolate, or replace a memory. | append-only mutation ledgers |
| GET | `/cell/{cell_id}/hygiene` | Hygiene report. | none |
| GET | `/cell/{cell_id}/sweep` | Read-only sweep analysis. | none |
| GET | `/cell/{cell_id}/proposals` | Proposal inbox projection. | none |
| POST | `/cell/{cell_id}/proposals/{proposal_id}/decision` | Record proposal decision. | append-only proposal decision ledger |
| GET | `/cell/{cell_id}/metrics` | Pilot metrics JSON. | none |
| GET | `/cell/{cell_id}/metrics.csv` | Pilot metrics CSV. | none |
| GET | `/cell/{cell_id}/operator-burden` | Operator-burden metrics subset. | none |
| GET | `/cell/{cell_id}/policy-tuning` | Policy tuning diagnostics. | none |
| POST | `/cell/{cell_id}/pack` | cell-scoped pack request. | retrieval/diagnostic logs may be appended |
| POST | `/cell/{cell_id}/feedback` | cell-scoped feedback report. | append-only feedback/feedback ledgers and counters |
| GET | `/diagnostics` | Diagnostic log query. | none |
| POST | `/readiness` | Replacement-readiness report. | none unless replay fixture explicitly requested by caller |

## Safety boundaries

- cell ledgers remain canonical truth.
- API writes are local append-only events or review decisions, not hidden state replacement.
- No endpoint requires external credentials for the synthetic examples.
- Use filesystem permissions and localhost binding as part of the local trust boundary.
