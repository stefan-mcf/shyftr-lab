# ShyftR Phase 11 Handoff Packet: External Memory Benchmarking

Date: 2026-05-17
Repo: `/Users/stefan/ShyftR`
Baseline HEAD: `88a1871313705d41f4b3cbb055fe46f83cd10e00`
Status: P11-1 implemented and verified locally; ready for review/commit or P11-2 mem0 OSS planning

## Current truth

Phase 10 is committed and pushed. Phase 11 is the next roadmap phase.

Phase 11 is external memory benchmarking. P11-0 documentation and P11-1 fixture-safe adapter harness are implemented locally. The next tranche is P11-2 mem0 OSS compatibility. Continue avoiding unsupported performance claims.

## Canonical documents

Read these first:

- `/Users/stefan/ShyftR/2026-05-17-shyftr-phase-11-external-memory-benchmarking-tranched-plan.md`
- `/Users/stefan/ShyftR/docs/benchmarks/methodology.md`
- `/Users/stefan/ShyftR/docs/benchmarks/adapter-contract.md`
- `/Users/stefan/ShyftR/docs/benchmarks/report-schema.md`
- `/Users/stefan/ShyftR/docs/benchmarks/fixture-schema.md`
- `/Users/stefan/ShyftR/docs/benchmarks/README.md`
- `/Users/stefan/ShyftR/2026-05-17-shyftr-phase-11-p11-1-benchmark-adapter-harness-closeout.md`

## Immediate continuation point

P11-1 is the current local implementation truth. Review the closeout, then either commit the P11-0/P11-1 work or continue to P11-2 mem0 OSS compatibility.

Do not jump directly into full LOCOMO, LongMemEval, or BEAM runs. First add mem0 OSS as an optional comparator against the same tiny synthetic fixture.

## P11-0 done-means

P11-0 is done when:

- methodology doc exists and names datasets, metrics, comparator systems, claim rules, and non-goals;
- adapter-contract doc exists and defines the neutral backend shape;
- report and fixture schema docs exist and define the first JSON contracts;
- the root phase plan exists;
- this handoff packet exists;
- public terminology and readiness checks pass;
- no public benchmark claim is made.

## Recommended next implementation step

Start P11-2: mem0 OSS compatibility.

1. add `src/shyftr/benchmarks/adapters/mem0_backend.py`;
2. detect missing mem0 dependency and report `skipped`;
3. keep mem0 Cloud optional and credential-gated;
4. run the same synthetic fixture against ShyftR, no-memory, and mem0 OSS when available;
5. update docs with local setup and exact run commands.

Only after P11-2 is green should LOCOMO-mini support begin.

## Non-goals for the next operator

Do not:

- claim ShyftR beats mem0;
- require mem0 Cloud credentials for local tests;
- vendor large third-party datasets;
- put real private memory data into benchmark fixtures;
- weaken ShyftR review-gated policy to chase recall numbers;
- skip token, cost, latency, and limitation reporting.

## Verification commands

P11-0 docs:

```bash
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

P11-1 implementation:

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_adapter_contract.py
PYTHONPATH=.:src pytest -q
```
