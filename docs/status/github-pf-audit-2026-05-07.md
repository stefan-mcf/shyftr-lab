# ShyftR GitHub public-facing audit

Status: PASS with one local-worktree hygiene note; no public-release blocker found.
Date: 2026-05-07
Audited commit: `9b670ba1b414527ebe7c1fe92c6cb1b5f9cbde85`
Repository: `stefan-mcf/shyftr`
Visibility: public
CI run: https://github.com/stefan-mcf/shyftr/actions/runs/25466682399

## Verdict

The public GitHub surface is ready for the completed implementation-tranches plan closeout. The repository presents ShyftR as a stable local-first release, keeps hosted platform operation and multi-tenant deployment outside the current public release, and has exact-SHA CI success for the closeout commit.

No blocker or high-severity remediation is required before treating the plan as closed through Checkpoint F.

## Scope inspected

- Git state, remote, branch, pushed SHA, and GitHub visibility.
- GitHub description, topics, commit attribution, contributors, and CI runs.
- README, package metadata, status docs, release gate, CI workflow, examples, scripts, and contribution/security surface.
- Public privacy scan, generated-artifact scan, large-object scan, binary scan, line-ending/.gitattributes scan, and dependency-license summaries.
- Local and remote verification evidence from the closeout commit.

## GitHub repository metadata

| Field | Value |
|---|---|
| Owner/repo | `stefan-mcf/shyftr` |
| Visibility | public |
| Default branch | `main` |
| Description | `Attachable recursive memory cells for AI agents` |
| Topics | `agentic-ai`, `ai-agents`, `memory`, `rag`, `vector-search`, `agent-memory`, `ai-memory`, `recursive-memory` |
| Commit author/committer | `stefan-mcf` using noreply email |
| Contributors endpoint | `stefan-mcf` only |
| Exact remote SHA | `9b670ba1b414527ebe7c1fe92c6cb1b5f9cbde85` |
| Exact-SHA CI | success |

## Audit findings

### F-01: plan closeout public posture is coherent

- severity: pass
- evidence: `README.md`, `docs/status/release-readiness.md`, `docs/status/phase-14-checkpoint-f-closeout.md`, `pyproject.toml`, `scripts/release_gate.sh`.
- public impact: readers see a stable local-first release posture instead of stale active alpha posture.
- result: PASS.

### F-02: release gate and CI match current posture

- severity: pass
- evidence: `scripts/release_gate.sh` ends with `SHYFTR_RELEASE_READY`; `.github/workflows/ci.yml` runs the release gate in the smoke job.
- public impact: the published repo has an exact, repeatable current release check.
- result: PASS.

### F-03: privacy and public-surface scan has no blocker

- severity: pass
- evidence: broad grep for local absolute paths, secret markers, private keys, runtime state, memory profile filenames, auth JSON, and environment files found policy text, examples, package lock dependency names, and historical planning references, but no live secret or private data blocker.
- public impact: no public-history mutation is required from this audit.
- result: PASS.

### F-04: clone hygiene is acceptable

- severity: pass
- evidence: no tracked ignored files; no large blobs above the audit threshold; no tracked binary/image/archive hits; `.gitattributes` exists; line endings are controlled.
- public impact: fresh clones stay small and professional.
- result: PASS.

### F-05: dependency license posture is acceptable

- severity: pass
- evidence: Python license inventory in an isolated uv venv reports ShyftR as MIT-licensed; console license summary reports MIT/ISC/Apache/BSD/MIT-0/CC-BY-4.0 dependencies.
- public impact: no license blocker identified.
- result: PASS.

### F-06: local worktree contains unrelated nonignored untracked docs

- severity: polish / local hygiene
- evidence: `git ls-files --others --exclude-standard` reported:
  - `docs/plans/2026-05-07-runtime-continuity-provider-tranched-plan.md`
  - the untracked context-compaction integration viability note
- public impact: none for the pushed public repo because these files are not tracked or pushed. They should be intentionally classified before any future commit.
- required remediation: either commit them in a separate continuity-provider planning change after review, move them to ignored private planning, or delete them if obsolete.
- result: nonblocking local hygiene note.

## Verification commands and results

| Check | Command | Result |
|---|---|---|
| Exact-SHA CI | `gh run watch 25466682399 --repo stefan-mcf/shyftr --exit-status` | PASS |
| Public readiness | `.venv/bin/python scripts/public_readiness_check.py` | PASS |
| Terminology stale guard | `.venv/bin/python scripts/terminology_inventory.py --fail-on-public-stale` | PASS |
| Terminology capitalization guard | `.venv/bin/python scripts/terminology_inventory.py --fail-on-capitalized-prose` | PASS |
| Full local gate | `PYTHON=.venv/bin/python bash scripts/check.sh` | PASS; 890 tests passed |
| Release gate | `PYTHON=.venv/bin/python bash scripts/release_gate.sh` | PASS; final verdict `SHYFTR_RELEASE_READY` |
| Diff whitespace | `git diff --check` | PASS before closeout commit |
| GitHub metadata | `gh repo view`, topics API, commits API, contributors API | PASS |
| Large object scan | `git rev-list --objects --all ... >1MB` | PASS; no hits |
| Binary scan | `git ls-files -z | xargs -0 file ...` | PASS; no hits |
| Tracked ignored files | `git ls-files -ci --exclude-standard` | PASS; no hits |

## Remediation plan

No required remediation tranches are open for the implementation-tranches closeout.

Recommended future polish only:

1. Classify the two nonignored untracked continuity-provider planning docs before the next commit.
2. If ShyftR later publishes packages or release tags, run a separate package-release audit covering build artifacts, release notes, versioning, signing, and distribution metadata.
3. If hosted or multi-tenant operation is later approved, run a separate deployment/security audit; the current pass does not authorize that scope.

## Final publication gate

- Local commit was pushed to `origin/main`.
- Remote `main` equals audited SHA `9b670ba1b414527ebe7c1fe92c6cb1b5f9cbde85`.
- GitHub Actions succeeded for that exact SHA.
- Visibility is public.
- Attribution maps to `stefan-mcf`.
- No blocker/high public-facing findings remain.

Final verdict: PASS.
