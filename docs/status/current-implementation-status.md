# ShyftR Current Implementation Status

Status: local-first alpha / controlled-pilot developer-preview MVP.

This document is the public truth source for what ShyftR implements today. Cell ledgers are canonical truth; Grid, API, console, reports, and profile artifacts are projections or local append-only writers.

## Current release posture

ShyftR is a local-first alpha MVP for controlled pilots. It is not a hosted SaaS product, not a multi-tenant production service, and not published as a package release. The supported path is cloning the repository, installing it in a Python 3.11+ environment, and running local Cells on synthetic or operator-approved data.

## Capability matrix

| Capability | Status | Public claim allowed | CLI surface | API/UI surface | Source modules | Test evidence | Caveats |
|---|---:|---|---|---|---|---|---|
| Cell init/layout | implemented | yes | `shyftr init-cell` / `shyftr init` | cells are listed by local service | `src/shyftr/layout.py` | `tests/test_layout.py`, `tests/test_cli.py` | Local filesystem only. |
| Pulse ingestion | implemented | yes | `shyftr ingest` / `shyftr feed` | `POST /ingest` via adapter config | `src/shyftr/ingest.py` | `tests/test_ingest.py`, `tests/test_file_adapter.py` | Existing `Source` compatibility remains. |
| Spark extraction/review | implemented | yes, with legacy alias note | `shyftr spark`, `shyftr approve`, `shyftr reject` | console Spark queue and review endpoint | `src/shyftr/extract.py`, `src/shyftr/review.py` | `tests/test_extract.py`, `tests/test_review.py`, `tests/test_console_api.py` | Legacy Fragment terms remain in compatibility APIs. |
| Charge promotion | implemented | yes | `shyftr charge` / `shyftr promote` | Charge explorer and lifecycle action endpoints | `src/shyftr/promote.py`, `src/shyftr/mutations.py` | `tests/test_promote.py`, `tests/test_memory_mutations.py` | Compatibility fields still use Trace identifiers in places. |
| Sparse retrieval and Grid metadata | implemented | yes | `shyftr search`, `shyftr retrieve`, `shyftr grid status/rebuild/smoke` | read-only Grid status through console summary | `src/shyftr/retrieval/*` | `tests/test_sparse_retrieval.py`, `tests/test_grid_metadata.py`, `tests/test_vector_retrieval.py` | Vector smoke uses deterministic local embeddings by default. |
| Hybrid retrieval | partial | qualified | covered through loadout/retrieval code paths | not a standalone public UI claim | `src/shyftr/retrieval/hybrid.py` | `tests/test_hybrid_retrieval.py` | Keep claims tied to tests and local deterministic behavior. |
| Profile projection | implemented | yes | `shyftr profile` | not first-class UI | `src/shyftr/profile.py` | `tests/test_profile.py` | Projection is rebuildable, not canonical truth. |
| Pack generation | implemented | yes | `shyftr pack` / `shyftr loadout` | `POST /pack`, Cell pack endpoint | `src/shyftr/loadout.py`, `src/shyftr/integrations/loadout_api.py` | `tests/test_loadout.py`, `tests/test_loadout_api.py` | Legacy Loadout naming remains as CLI alias and data compatibility. |
| Signal recording | implemented | yes | `shyftr signal` / `shyftr outcome` | `POST /signal`, Cell signal endpoint | `src/shyftr/outcomes.py`, `src/shyftr/integrations/outcome_api.py` | `tests/test_outcomes.py`, `tests/test_outcome_api.py` | Legacy Outcome naming remains as CLI alias and data compatibility. |
| Diagnostics/readiness/hygiene/audit reports | implemented | yes | `shyftr diagnostics`, `shyftr readiness`, `shyftr hygiene`, `shyftr audit` | diagnostics/readiness endpoints and console metrics | `src/shyftr/observability.py`, `src/shyftr/readiness.py`, `src/shyftr/reports/` | `tests/test_hygiene.py`, `tests/test_replacement_readiness.py`, `tests/test_audit.py` | Reports are local evidence, not external compliance certification. |
| Sweep/proposal/challenge/isolation workflows | implemented for local advisory loops | qualified | `shyftr sweep`, `shyftr challenge`, `shyftr proposals export` | proposal inbox and decision endpoints | `src/shyftr/sweep.py`, `src/shyftr/audit/`, `src/shyftr/integrations/proposals.py` | `tests/test_sweep.py`, `tests/test_challenger.py`, `tests/test_runtime_proposals.py`, `tests/test_isolation_challenge_workflow.py` | Advisory proposals are review-gated. |
| Backup/restore | implemented | yes | `shyftr backup`, `shyftr restore` | not exposed in console | `src/shyftr/backup.py` | `tests/test_backup_restore.py` | Local archive output only; generated archives should not be committed. |
| Ledger verification/adoption | implemented | yes | `shyftr verify-ledger --adopt` / `shyftr verify-ledger` | not exposed in console | `src/shyftr/ledger_verify.py` | `tests/test_ledger_verification.py` | Adoption writes current ledger-head manifest after operator chooses to trust current state. |
| Privacy/sensitivity and policy scoping | implemented | yes | enforced through Pack/provider paths | policy effects visible through console metrics and diagnostics | `src/shyftr/privacy.py`, `src/shyftr/policy.py` | `tests/test_privacy_sensitivity.py`, `tests/test_policy.py` | This is local policy enforcement, not a guarantee for arbitrary external runtimes. |
| Local HTTP service | implemented as optional adapter | yes, local-only | `shyftr serve --host 127.0.0.1 --port 8014` | FastAPI endpoints | `src/shyftr/server.py` | `tests/test_server.py` | Requires `.[service]`; bind to localhost for normal use. |
| React console | implemented as local console | qualified | npm scripts under `apps/console` | browser UI backed by local service | `apps/console/src/**`, `src/shyftr/console_api.py` | `tests/test_console_api.py`, console build | Developer preview UI; no hosted deployment is claimed. |
| Runtime adapter examples | implemented as fixtures and protocol demos | yes | `shyftr adapter validate/discover/ingest/backfill/sync` | service adapter endpoints | `src/shyftr/integrations/*` | `tests/test_runtime_integration_demo.py`, `tests/test_integration_cli.py` | Examples are synthetic and runtime-neutral. |
| Trusted memory provider integration | partial | qualified | provider modules and tests only | no hosted provider control plane | `src/shyftr/trusted_memory.py`, `src/shyftr/memory_provider.py` | `tests/test_trusted_memory.py`, `tests/test_memory_provider.py` | Controlled-pilot integration surface; do not imply managed backend replacement for all domains. |
| Coil/Rail distillation | partial/planned | qualified/no current broad claim | older compatibility modules/tests | no public UI claim | `src/shyftr/alloys.py`, doctrine docs | `tests/test_alloys.py`, `tests/test_doctrine.py` | Treat as future-facing unless directly citing tested local behavior. |
| Distributed multi-cell intelligence | not implemented | no current-capability claim | none | none | no current implementation surface | no current alpha test evidence | Outside the current alpha boundary. |

## Public wording rule

Use current-tense claims only for implemented rows above. Use future-tense or explicit not-current wording for planned and deferred concepts. Public-facing status docs should say alpha plainly rather than referencing internal planning labels.
