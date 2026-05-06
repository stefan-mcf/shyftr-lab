# ShyftR Public Readiness Audit

Status: public alpha baseline published; ongoing hardening and controlled-pilot testing continue through explicit gates.

## Repository identity

| Field | Value |
|---|---|
| Checkout path | Repository root |
| Remote | `https://github.com/stefan-mcf/shyftr.git` |
| GitHub repo | `stefan-mcf/shyftr` |
| Visibility at audit start | private; public alpha baseline published after clean one-commit export |
| Branch at audit start | `main...origin/main [ahead 8]` |
| Cleanup boundary | local files only; no push, visibility flip, tag, package publish, or history rewrite |
| Commit identity for cleanup | `stefan-mcf <73107236+stefan-mcf@users.noreply.github.com>` |

## Findings register

| ID | Severity | Finding | Resolution status | evidence / action |
|---|---:|---|---|---|
| F-01 | high | README was vision-heavy and not optimized as a public landing page. | resolved locally | README rewritten to status/quickstart/safety/docs/checks. |
| F-02 | high | Public current-capability truth source was missing. | resolved locally | Added `docs/status/current-implementation-status.md`. |
| F-03 | high | Durable public-readiness audit report was missing. | resolved locally | This report records findings, scans, decisions, and gates. |
| F-04 | blocker until classified | Historical docs contain local/private and future-planning material. | classified; deletion deferred | Historical/source/plan docs are classified below; deletion or history rewrite requires approval. |
| F-05 | high | Existing history used placeholder attribution. | partially resolved | Local cleanup identity set to noreply; historical attribution is a publication decision item. |
| F-06 | high | Repo was private and local branch was ahead of origin. | publication gate | Remote mutation blocked until explicit approval and exact-SHA verification. |
| F-07 | high | Verification commands needed clean install context. | resolved locally | Added install/development docs and smoke scripts using Python 3.11+ and `.[dev,service]`. |
| F-08 | medium/high | CI did not cover service extras, console, example smoke, or readiness scan. | resolved locally | CI updated with Python, smoke, console, and readiness jobs. |
| F-09 | medium | `.gitignore` missed release/runtime artifact classes. | resolved locally | `.gitignore` expanded for Hermes plans, coverage, caches, example output, backups. |
| F-10 | medium | Local ignored artifacts needed classification. | resolved locally | Readiness script checks tracked ignored files and risky untracked files. |
| F-11 | medium | API and console docs were incomplete. | resolved locally | Added `docs/api.md` and `docs/console.md`. |
| F-12 | medium | Examples lacked a public map and deterministic lifecycle script. | resolved locally | Added `examples/README.md` and `examples/run-local-lifecycle.sh`. |
| F-13 | medium | package metadata and release stance were ambiguous. | resolved locally | `pyproject.toml` metadata updated while retaining version `0.0.0`. |
| F-14 | medium | Contributor/security/community surface was incomplete. | resolved locally | Added CONTRIBUTING, SECURITY, CHANGELOG, CODE_OF_CONDUCT, PR and issue templates. |
| F-15 | high | Public docs needed a clear alpha/future-capability boundary. | resolved locally | Public-facing status and README mark ShyftR as alpha without internal planning references. |
| F-16 | medium | Public readiness scan was ad hoc and missed tracked docs/plans/source notes. | resolved locally | `scripts/public_readiness_check.py` now scans tracked public docs, examples, scripts, and GitHub metadata paths, with regression tests for local path leaks. |
| F-17 | medium | Full gate needed normalized environment. | resolved locally | `scripts/smoke-install.sh` creates a temp venv and installs extras. |
| F-18 | medium | `.hermes/plans` was untracked and could leak. | resolved locally | `.hermes/` ignored; public-safe summary lives in this report. |
| F-19 | medium | Large-object, line-ending, dependency-license, and codebase composition checks were incomplete. | resolved locally | Added `.gitattributes`; project-specific Python license inventory, Node dependency license summary, and pygount composition evidence are recorded below. |

## Historical and future-doc classification

Current docs intended as public navigation and evidence: `README.md`, `docs/status/**`, `docs/development.md`, `docs/example-lifecycle.md`, `docs/runtime-integration-example.md`, `docs/api.md`, `docs/console.md`, `docs/concepts/**`, `examples/**`, and GitHub community files.

Existing files under `docs/plans/**`, `docs/sources/**`, `docs/feeds/**`, and `docs/runbooks/**` are classified as historical implementation notes, source concept notes, or controlled-pilot runbooks. They may contain future concepts or historical runtime names. They must not be treated as current product capability. Removing, rewriting, or excluding them from a public-history export is a final publication decision and is not performed autonomously in this cleanup.

## Scan and gate summary

Latest local gate run: 2026-05-06.

| Gate | Command | Latest local result |
|---|---|---|
| Python environment | `uv venv --python python3.11 /tmp/shyftr-public-verify-venv` | PASS; Python 3.11.13 |
| Install with extras | `uv pip install --python /tmp/shyftr-public-verify-venv/bin/python -e '.[dev,service]'` | PASS; FastAPI test dependency gap fixed by adding `httpx` to `service` extra |
| Python tests | `/tmp/shyftr-public-verify-venv/bin/python -m pytest -q` | PASS; 747 passed |
| Focused API/console/example tests | `/tmp/shyftr-public-verify-venv/bin/python -m pytest tests/test_demo_flow.py tests/test_runtime_integration_demo.py tests/test_server.py tests/test_console_api.py -q` | PASS; 32 passed |
| Demo lifecycle | `PATH=/tmp/shyftr-public-verify-venv/bin:$PATH PYTHON=/tmp/shyftr-public-verify-venv/bin/python bash examples/run-local-lifecycle.sh` | PASS |
| Smoke install | `bash scripts/smoke-install.sh` | PASS with uv-backed temp venv |
| Full local check | `PATH=/tmp/shyftr-public-verify-venv/bin:$PATH PYTHON=/tmp/shyftr-public-verify-venv/bin/python bash scripts/check.sh` | PASS; includes pytest, lifecycle, console build/audit, readiness |
| Console build/audit | `(cd apps/console && npm run build && npm audit --omit=dev)` | PASS; build completed and 0 vulnerabilities reported |
| Public readiness | `python scripts/public_readiness_check.py` | PASS; tracked docs/plans/source notes included in private-path scan |
| Artifact scan | `git ls-files -ci --exclude-standard` | PASS; no tracked ignored files |
| Large object scan | `git rev-list --objects --all ... >1MB` | PASS; no blobs above threshold reported |
| Binary scan | `git ls-files -z \| xargs -0 file ...` | PASS; no tracked binary/image/archive hits reported |
| Python dependency license inventory | `uv venv --python python3.11 /tmp/shyftr-license-venv`; `uv pip install --python /tmp/shyftr-license-venv/bin/python -e . pip-licenses`; `/tmp/shyftr-license-venv/bin/pip-licenses --format=markdown --with-urls` | PASS; isolated project install reports ShyftR itself as MIT-licensed with no third-party runtime Python packages |
| Console dependency license inventory | `cd apps/console && npx --yes license-checker --summary --excludePrivatePackages` | PASS; third-party console packages summarize as MIT 137, ISC 8, Apache-2.0 4, BSD-2-Clause 2, BSD-3-Clause 2, MIT-0 1, CC-BY-4.0 1; local private `@shyftr/console` package has explicit MIT metadata in `package.json`/lockfile |
| Codebase composition | `uvx --from pygount pygount --format=summary --folders-to-skip='.git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,.eggs,*.egg-info' .` | PASS; 210 counted files, 19,738 code lines, 10,917 comment/doc lines; primary code is Python with small TypeScript/TSX console surface |
| Diff whitespace | `git diff --check` | PASS |
| Independent review | read-only repo review | PASS; independent review returned no blockers |

## Publication decision

Completed: the public repository was published as a clean one-commit alpha baseline after private-side gates, clean-history export verification, CI, public visibility verification, unauthenticated clone checks, and fresh-clone readiness scans.

Current rule: keep the repo clearly labelled as local-first alpha / controlled-pilot. Before inviting outside technical testers, run `bash scripts/alpha_gate.sh` and expect `ALPHA_GATE_READY`. Do not direct testers to use sensitive production memory until operator dogfooding, readiness reports, diagnostics, and fallback/archive evidence support a bounded pilot.
