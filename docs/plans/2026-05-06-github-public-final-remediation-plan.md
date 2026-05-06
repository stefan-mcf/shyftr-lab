# ShyftR Final GitHub Public Remediation Plan

> For Hermes: execute these tranches before any push/public-promotion claim. Do not push, change visibility, tag releases, or publish packages without an explicit operator gate. This plan was produced from the final `github-pf-audit` run on 2026-05-06.

**Goal:** clear the final public-facing blockers found after the plain-language lifecycle rename so the local rename commit can be reconciled with public `main`, verified, pushed under approval, and proven by exact-SHA GitHub Actions.

**Repository:** the repository root
**GitHub repo:** `stefan-mcf/shyftr`
**Visibility:** public
**Local branch state at audit:** `main...origin/main [ahead 1, behind 2]`
**Local HEAD at audit:** `19e7f5598fe98f58cf15180dbf2ddcb0a4811977`
**Remote main at audit:** `f96210847619d3e1b9ee3dfef4ce4ac710728370`

---

## Audit Evidence Summary

Current repo state:
- GitHub auth resolved to `stefan-mcf`.
- Remote repo `stefan-mcf/shyftr` is public, default branch `main`.
- Local `main` contains the plain-language rename commit, but remote `main` has two newer documentation commits.
- Local gates passed: `scripts/check.sh`, `scripts/alpha_gate.sh`, terminology stale guard, terminology capitalization guard, and `git diff --check`.
- Public clone hygiene scans were clean for nonignored untracked files, tracked ignored files, large tracked blobs over 1 MB, and tracked binaries.
- Secret/credential scan found no real credentials; matches were policy/docs/tests/package-lock/code regex references.
- Sensitive family-name scan returned zero tracked paths.

Audit findings:

- **F-01: Local and remote main have diverged**
  - Severity: blocker
  - Evidence: `git status --short --branch` showed `main...origin/main [ahead 1, behind 2]`; local HEAD `19e7f5598fe98f58cf15180dbf2ddcb0a4811977`; remote main `f96210847619d3e1b9ee3dfef4ce4ac710728370`.
  - Public-release impact: local rename work cannot be pushed as a clean fast-forward and has not been verified by GitHub Actions on the exact public SHA.
  - Required remediation: rebase or merge the local rename commit onto `origin/main`, resolve conflicts, rerun full gates, then push only after approval.
  - Plan mapping: Tranche 1, Final Tranche

- **F-02: Public tracked docs expose local absolute paths**
  - Severity: blocker
  - Evidence: tracked markdown under `docs/plans/`, `docs/runbooks/`, `docs/sources/`, and `docs/status/` contains `operator-local` paths, including local checkout and Desktop source-document paths.
  - Public-release impact: exposes local filesystem structure and operator-local document provenance in a public repo.
  - Required remediation: replace absolute local paths with repo-relative paths, generic examples, or sanitized provenance wording; decide whether old planning/source notes remain public.
  - Plan mapping: Tranche 2

- **F-03: Public-readiness check misses the leaking doc paths**
  - Severity: blocker
  - Evidence: `scripts/public_readiness_check.py` passed while `git grep` found local absolute paths outside its scanned `CURRENT_PUBLIC_PATHS`; its private path regex also allows the repository root.
  - Public-release impact: the readiness gate can report PASS while public docs still leak local paths.
  - Required remediation: expand readiness scanning to the full tracked public documentation surface and reject local absolute paths by default.
  - Plan mapping: Tranche 3

- **F-04: Exact-SHA GitHub CI is missing for the local rename commit**
  - Severity: blocker
  - Evidence: GitHub Actions success exists for remote `f962108...`, not local `19e7f55...`.
  - Public-release impact: local verification is strong but public GitHub verification is absent for the commit intended to ship.
  - Required remediation: reconcile, push after approval, then verify GitHub Actions success on the exact pushed SHA.
  - Plan mapping: Final Tranche

- **F-05: Python dependency-license inventory is inconclusive**
  - Severity: high
  - Evidence: `pip-licenses` was run against the global environment rather than an isolated ShyftR project environment.
  - Public-release impact: cannot make a strong project-specific Python dependency-license claim.
  - Required remediation: run license inventory from an isolated project install or document that there are no runtime Python third-party dependencies requiring inventory beyond package metadata.
  - Plan mapping: Tranche 4

- **F-06: Node dependency license summary includes one `UNLICENSED` entry**
  - Severity: high
  - Evidence: `npx license-checker --summary` under `apps/console` reported `UNLICENSED: 1`.
  - Public-release impact: public repo/license posture needs this package identified and classified as acceptable dev tooling, internal app metadata, or a dependency issue.
  - Required remediation: identify the package and document or remediate it.
  - Plan mapping: Tranche 4

- **F-07: CODE_OF_CONDUCT.md is missing**
  - Severity: polish
  - Evidence: required-file check showed `MISS CODE_OF_CONDUCT.md`.
  - Public-release impact: small solo alpha repos can ship without one, but community-facing GitHub polish is incomplete.
  - Required remediation: add a concise Contributor Covenant or intentionally document that it is deferred.
  - Plan mapping: Tranche 5

- **F-08: Codebase size/language inventory was inconclusive**
  - Severity: polish
  - Evidence: `pygount` was unavailable/mis-invoked; only rough tracked-file counts were captured.
  - Public-release impact: audit evidence lacks a clean codebase composition summary.
  - Required remediation: either install/use `pygount` correctly or record tracked-file composition as the accepted inventory.
  - Plan mapping: Tranche 5

---

## Definition of Done

This plan is complete when:
- local `main` is reconciled with `origin/main`;
- all tracked public docs are free of local absolute path leaks;
- `scripts/public_readiness_check.py` fails on fixture/local path leaks and passes on the sanitized tree;
- dependency-license findings are resolved or explicitly documented;
- optional community polish is complete or intentionally deferred;
- local gates pass after reconciliation;
- a local remediation commit exists;
- push remains gated by explicit approval;
- after any approved push, GitHub Actions passes for the exact pushed SHA and local/remote SHA equality is verified.

---

## Tranche 1 — Reconcile Local Rename Work with Remote Main

**Findings addressed:** F-01

**Objective:** bring the local rename commit onto the current public branch history without losing either the remote portfolio/readiness polish or the local plain-language rename work.

**Files:**
- Modify as needed only for conflict resolution.

**Tasks:**
1. Fetch remote state:
   ```bash
   git fetch origin --prune
   git status --short --branch
   git log --oneline --decorate --graph --left-right --cherry-pick --boundary HEAD...origin/main
   ```
2. Rebase local work onto remote main unless conflict shape makes merge safer:
   ```bash
   git rebase origin/main
   ```
3. Resolve conflicts deliberately, preserving:
   - remote documentation/readiness polish from `d8710c9` and `f962108`;
   - local plain-language terminology migration from `19e7f55`;
   - compatibility aliases and terminology guards.
4. After conflict resolution, inspect affected files:
   ```bash
   git status --short --branch
   git diff --check
   git diff origin/main...HEAD --stat
   ```

**Acceptance Criteria:**
- `git status --short --branch` no longer reports `behind 2`.
- The plain-language rename changes remain present.
- Remote readiness/documentation changes remain present.
- No unresolved conflicts remain.

**Verification:**
```bash
git status --short --branch
git diff --check
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
```

---

## Tranche 2 — Sanitize Local Absolute Paths in Public Docs

**Findings addressed:** F-02

**Objective:** remove local filesystem disclosures from tracked public documentation while keeping useful historical/provenance context.

**Files:**
- Modify:
  - `docs/plans/2026-04-24-shyftr-active-learning-follow-up-plan.md`
  - `docs/plans/2026-04-24-shyftr-implementation-tranches.md`
  - `docs/plans/2026-04-24-shyftr-runtime-integration-adapter-plan.md`
  - `docs/plans/2026-04-24-shyftr-universal-memory-substrate-plan.md`
  - `docs/plans/2026-05-06-shyftr-plain-language-canonical-rename-plan.md`
  - `docs/runbooks/phase-4-to-5-goal-prompt.md`
  - `docs/status/public-readiness-audit.md`
  - `docs/sources/2026-05-01-dream-logging-interpretation-app-concept.md`
  - `docs/sources/2026-05-01-language-learning-app-concept-shyftr-powered.md`
  - `docs/sources/2026-05-01-shyftr-antaeus-hermes-integration-strategy.md`
  - `docs/sources/2026-05-01-shyftr-cells-mounts-policies.md`
  - `docs/sources/2026-05-01-shyftr-future-concepts-frontier-features.md`
  - `docs/sources/2026-05-01-shyftr-naming-conventions.md`
  - `docs/sources/2026-05-01-shyftr-startup-business-concept.md`

**Tasks:**
1. Replace local checkout commands such as `cd the repository root` with repo-relative or generic forms:
   ```text
   From the repository root:
   ```
2. Replace lab path references with generic private-workspace wording:
   ```text
   Run from a private ShyftR lab checkout:
   ```
3. Replace Desktop source-document paths with sanitized provenance:
   ```text
   > Source: operator-local concept document, sanitized into this public note.
   ```
4. In `docs/status/public-readiness-audit.md`, replace the local path row with a repo-relative or generic location.
5. Run a full tracked-doc path scan:
   ```bash
   git grep -n -I -E '/path/to/|/home/' -- docs README.md CONTRIBUTING.md SECURITY.md CHANGELOG.md .github examples scripts pyproject.toml || true
   ```
6. Review remaining matches and keep only intentional regex/test examples in source/tests, not public prose.

**Acceptance Criteria:**
- No public markdown prose under `docs/`, `.github/`, examples, README, or status docs exposes local absolute paths.
- Any remaining `/path/to/` or `/home/` matches are implementation regexes or tests, not public docs.
- Public provenance remains understandable without local machine details.

**Verification:**
```bash
git grep -n -I -E '/path/to/|/home/' -- docs README.md CONTRIBUTING.md SECURITY.md CHANGELOG.md .github examples scripts pyproject.toml || true
python scripts/public_readiness_check.py
```

---

## Tranche 3 — Harden Public Readiness Guard Coverage

**Findings addressed:** F-03

**Objective:** make `scripts/public_readiness_check.py` catch the exact class of public-surface leaks found by the audit.

**Files:**
- Modify:
  - `scripts/public_readiness_check.py`
- Modify or create tests as appropriate:
  - `tests/test_public_readiness_check.py` or existing readiness tests

**Tasks:**
1. Expand the scanned public surface to include all tracked markdown/docs intended for public GitHub, especially:
   - `docs/`
   - `.github/`
   - `examples/`
   - top-level public markdown files
   - public scripts/readiness files
2. Replace the current permissive private path regex with a default rejection for local absolute paths:
   ```python
   re.compile(r"/(Users|home)/[^\s`)]+")
   ```
   Then add narrow allowlisting only for source-code regex literals or tests when necessary.
3. Add a regression test or fixture that fails if `docs/plans/...` or `docs/sources/...` contains `/path/to/example/...`.
4. Ensure `scripts/public_readiness_check.py` still distinguishes real leaks from source-code regex/test fixtures.
5. Run readiness and terminology checks.

**Acceptance Criteria:**
- The readiness script would have failed on the audited local path leaks.
- The readiness script passes after Tranche 2 sanitization.
- Guard scope is obvious from code and tests.

**Verification:**
```bash
python scripts/public_readiness_check.py
python -m pytest tests/test_public_readiness_check.py -q  # if created
python -m pytest tests/test_replacement_readiness.py tests/test_terminology_inventory.py -q
```

---

## Tranche 4 — Resolve Dependency-License Audit Gaps

**Findings addressed:** F-05, F-06

**Objective:** produce a project-specific license posture instead of relying on global-environment noise.

**Files:**
- Modify if documentation is needed:
  - `docs/status/public-readiness-audit.md`
  - `docs/status/alpha-readiness.md`
  - `README.md` if a short note is useful
- Modify only if dependency/package metadata remediation is needed:
  - `apps/console/package.json`
  - `apps/console/package-lock.json`
  - `pyproject.toml`

**Tasks:**
1. Create or use an isolated Python environment for ShyftR dependency inspection:
   ```bash
   python3 -m venv /tmp/shyftr-license-venv
   /tmp/shyftr-license-venv/bin/python -m pip install -U pip
   /tmp/shyftr-license-venv/bin/python -m pip install -e . pip-licenses
   /tmp/shyftr-license-venv/bin/pip-licenses --format=markdown --with-urls
   ```
2. Record whether ShyftR has runtime third-party dependencies and whether licenses are compatible with the repo license.
3. Identify the Node `UNLICENSED` package:
   ```bash
   cd apps/console
   npx --yes license-checker --json > /tmp/shyftr-console-licenses.json
   python3 - <<'PY'
   import json
   data=json.load(open('/tmp/shyftr-console-licenses.json'))
   for name, meta in sorted(data.items()):
       if meta.get('licenses') == 'UNLICENSED':
           print(name, meta)
   PY
   ```
4. If `UNLICENSED` is the local package itself, document it as internal app metadata and consider adding an explicit license field matching the repo license.
5. If it is a third-party package, assess replacement, license metadata, or risk acceptance.

**Acceptance Criteria:**
- Python license inventory is project-specific or explicitly documented as not applicable.
- The Node `UNLICENSED` entry is identified and resolved/documented.
- No unresolved high license ambiguity remains for public readiness.

**Verification:**
```bash
/tmp/shyftr-license-venv/bin/pip-licenses --format=markdown --with-urls
cd apps/console && npx --yes license-checker --summary
```

---

## Tranche 5 — Public GitHub Polish and Audit Evidence Completion

**Findings addressed:** F-07, F-08

**Objective:** close non-blocking public polish gaps so the final audit is complete and repeatable.

**Files:**
- Create or intentionally defer:
  - `CODE_OF_CONDUCT.md`
- Modify:
  - `docs/status/public-readiness-audit.md`
  - optionally `README.md` or `CONTRIBUTING.md`

**Tasks:**
1. Add a concise `CODE_OF_CONDUCT.md`, preferably Contributor Covenant, unless deliberately deferred.
2. Complete codebase composition evidence using a working tool or tracked-file summary:
   ```bash
   python3 -m pip install --user pygount || true
   pygount --format=summary --folders-to-skip='.git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,.eggs,*.egg-info' .
   ```
   If `pygount` remains unavailable, record the tracked-file inventory instead:
   ```bash
   git ls-files | wc -l
   git ls-files | cut -d/ -f1 | sort | uniq -c
   ```
3. Update `docs/status/public-readiness-audit.md` with the final evidence bundle and any intentional deferrals.
4. Keep README concise; put detailed evidence in status docs.

**Acceptance Criteria:**
- Community-governance gap is resolved or explicitly accepted.
- Public-readiness audit evidence includes a repeatable codebase composition command/result.
- The status doc itself contains no local absolute paths.

**Verification:**
```bash
test -f CODE_OF_CONDUCT.md || grep -n "Code of Conduct" docs/status/public-readiness-audit.md
git grep -n -I -E '/path/to/|/home/' -- docs/status/public-readiness-audit.md || true
git diff --check
```

---

## Tranche 6 — Full Local Verification and Commit

**Findings addressed:** F-01 through F-08

**Objective:** prove the reconciled, sanitized tree locally and commit the remediation work without pushing.

**Files:**
- All modified files from Tranches 1-5.

**Tasks:**
1. Run the full local gate bundle:
   ```bash
   bash scripts/check.sh
   bash scripts/alpha_gate.sh
   python scripts/terminology_inventory.py --fail-on-public-stale
   python scripts/terminology_inventory.py --fail-on-capitalized-prose
   git diff --check
   ```
2. Run targeted public-surface scans:
   ```bash
   git grep -n -I -E '/path/to/|/home/' -- docs README.md CONTRIBUTING.md SECURITY.md CHANGELOG.md .github examples scripts pyproject.toml || true
   git grep -n -I -E 'api[_-]?key|secret|password|token|PRIVATE KEY|chat_id|state\.db|auth\.json|\.env' -- . || true
   git ls-files --others --exclude-standard
   git ls-files -ci --exclude-standard
   ```
3. Inspect staged files deliberately:
   ```bash
   git status --short
   git diff --stat
   git diff --check
   ```
4. Commit locally:
   ```bash
   git add <intended files>
   git commit -m "chore: close final public readiness audit gaps"
   ```

**Acceptance Criteria:**
- Full local gates pass.
- Public-surface scans have no unclassified leaks.
- Working tree is clean after commit.
- The commit is local only unless explicit push approval is given.

**Verification:**
```bash
git status --short --branch
git log --oneline -3
```

---

## Final Tranche — Push Gate, Exact-SHA CI, and Public Verification

**Findings addressed:** F-01, F-04

**Objective:** after explicit approval, publish the reconciled remediation commit and verify GitHub truth.

**Human Gate:** Stop before this tranche unless the operator explicitly approves push.

**Tasks after approval:**
1. Verify local state:
   ```bash
   git status --short --branch
   LOCAL_SHA=$(git rev-parse HEAD)
   echo "$LOCAL_SHA"
   ```
2. Push:
   ```bash
   git push origin main
   ```
3. Verify remote SHA equals local SHA:
   ```bash
   LOCAL_SHA=$(git rev-parse HEAD)
   REMOTE_SHA=$(HOME=$HOME gh api repos/stefan-mcf/shyftr/git/ref/heads/main --jq '.object.sha')
   test "$LOCAL_SHA" = "$REMOTE_SHA"
   ```
4. Verify GitHub Actions for exact SHA:
   ```bash
   HOME=$HOME gh run list --repo stefan-mcf/shyftr --limit 20 \
     --json databaseId,status,conclusion,headSha,workflowName,url \
     --jq '.[] | select(.headSha=="'"$LOCAL_SHA"'")'
   ```
5. If a run is in progress, watch it:
   ```bash
   HOME=$HOME gh run watch --repo stefan-mcf/shyftr --exit-status
   ```
6. Verify public metadata and attribution:
   ```bash
   HOME=$HOME gh repo view stefan-mcf/shyftr --json nameWithOwner,isPrivate,visibility,url,description,defaultBranchRef,repositoryTopics
   HOME=$HOME gh api repos/stefan-mcf/shyftr/commits/main \
     --jq '{sha:.sha, authorLogin:(.author.login // null), committerLogin:(.committer.login // null), authorEmail:.commit.author.email, committerEmail:.commit.committer.email}'
   HOME=$HOME gh api repos/stefan-mcf/shyftr/contributors \
     --jq '.[] | {login,contributions,html_url}'
   ```

**Acceptance Criteria:**
- Remote `main` equals local `HEAD`.
- GitHub Actions succeeds for the exact pushed SHA.
- Repo remains public with expected metadata/topics.
- Attribution maps to `stefan-mcf`.
- No additional visibility/release/package side effects occur.

**Verification:**
```bash
git status --short --branch
HOME=$HOME gh repo view stefan-mcf/shyftr --json nameWithOwner,visibility,url
```
