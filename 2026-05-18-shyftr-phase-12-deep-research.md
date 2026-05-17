# ShyftR Phase 12 deep research: standard-dataset and answer-eval track

Date: 2026-05-18
Repo: `/Users/stefan/ShyftR`
Starting commit: `bda4817884f3605bed30e9480563df7b6348bc56`
Status: research complete; implementation not started

## Starting truth

Phase 11 is complete and pushed. It delivered a fixture-safe benchmark harness, ShyftR/no-memory/optional mem0 OSS comparators, LOCOMO-mini, LOCOMO-standard local mapping and conversion scaffolds, timeout/resume/retry controls, final fixture reports, and a polished HTML closeout.

Phase 11 deliberately did not claim full LOCOMO, LongMemEval, BEAM, answer-quality, hosted, or broad superiority results.

## Research question

What should the next phase do to produce the best benchmark progress without weakening ShyftR's public-readiness posture?

Criteria:

- maximize external comparability against public memory-benchmark work;
- keep data local, operator-triggered, and private-by-default;
- avoid automatic large downloads and committed third-party datasets;
- preserve runner-owned evaluation so the memory backend is what changes, not the agent loop;
- make the first implementation tranche small enough to ship safely;
- defer expensive, credentialed, or LLM-judge behavior until deterministic scaffolds are proven.

## External benchmark findings

### LOCOMO

Upstreams:

- paper/project: `https://github.com/snap-research/locomo`
- dataset file observed in public repo: `data/locomo10.json`

Shape:

- around 10 multi-session dialogues;
- session keys such as `session_1`, `session_2`, etc.;
- each session has dated dialogue turns;
- questions include question, answer, category, and evidence identifiers.

Fit for ShyftR:

- Phase 11 already added LOCOMO-mini and LOCOMO-standard local mapping/conversion scaffolds.
- LOCOMO remains a good validation target once a public-safe/operator-local full file is supplied.
- Do not make LOCOMO the first Phase 12 implementation task because the mapping scaffolding is already present and the next highest-value gap is broader benchmark family coverage.

Caveat:

- licensing posture should be rechecked before public redistribution;
- do not vendor the dataset or publish private converted files.

### LongMemEval

Upstreams:

- project: `https://github.com/xiaowu0162/LongMemEval`
- Hugging Face dataset: `xiaowu0162/longmemeval-cleaned`

Observed shape:

- roughly 500 question objects;
- each question has its own haystack sessions;
- fields include question id, question type, question, answer, haystack sessions, haystack dates, haystack session ids, and question date;
- question types include temporal reasoning, multi-session, knowledge update, single-session user, single-session assistant, and preference.

Fit for ShyftR:

- Best first Phase 12 standard-dataset target.
- MIT licensing is comparatively clean.
- Per-question haystack shape is a strong test of benchmark-run design because each question must be isolated unless the runner explicitly supports per-case ingest/reset.
- The dataset is large enough to matter but smaller and less operationally risky than BEAM.

Caveat:

- the public dataset contains realistic personal-conversation-like content; ShyftR should treat it as private-by-default at conversion/run time unless an operator declares a public-safe local file;
- do not auto-download by default;
- initial implementation should map a normalized local file and use a tiny hand-crafted LongMemEval-shaped test payload.

### BEAM

Upstreams:

- Hugging Face dataset: `Mohammadta/BEAM`
- larger bucket: `Mohammadta/BEAM-10M`

Observed shape:

- multiple token buckets, including very large conversations;
- probing questions organized by memory ability category;
- ability classes include abstention, contradiction resolution, event ordering, information extraction, instruction following, knowledge update, multi-session reasoning, preference following, summarization, and temporal reasoning.

Fit for ShyftR:

- Valuable Phase 12/13 mapping target after LongMemEval and answer-eval scaffolds.
- Good stress test for cost/latency, resume, and chunking controls.
- Not the best first Phase 12 implementation tranche because payload size and schema breadth increase operational risk.

Caveat:

- CC BY-SA 4.0 attribution/share-alike obligations must be documented;
- large buckets require explicit human/operator choice and strict local artifact guards.

### Answer and judge evaluation

Current ShyftR state:

- Phase 11 reports declare `answerer_owned_by_runner: true` and `judge_owned_by_runner: true`, but answer/judge execution is disabled.
- `expected_answer`, `expected_item_ids`, `question_type`, and `temporal_hint` already exist in the fixture schema.
- Report docs already reserve answer metric ideas, but code does not compute them yet.

Best design:

- deterministic-first answer/judge track;
- optional LLM judge later, gated by explicit CLI flags and disclosed model/prompt/cost metadata;
- abstention-aware scoring with `answered`, `abstained_unknown`, and `abstained_insufficient` states;
- question-type buckets for factual, temporal, multi-hop, knowledge-update, preference, and abstention cases;
- support coverage that connects retrieved items to answer correctness.

Benchmark-theater guardrail:

- answer-quality results must name dataset, fixture/run id, answerer, judge, model config, prompt template, top-k, timeout/retry/resume policy, and limitations;
- no broad superiority claims;
- deterministic judges are the default because they are reproducible and cost-free.

## Repo audit findings

Implemented surfaces:

- `src/shyftr/benchmarks/types.py`
- `src/shyftr/benchmarks/fixture.py`
- `src/shyftr/benchmarks/runner.py`
- `src/shyftr/benchmarks/report.py`
- `src/shyftr/benchmarks/locomo_standard.py`
- `src/shyftr/benchmarks/adapters/base.py`
- `src/shyftr/benchmarks/adapters/shyftr_backend.py`
- `src/shyftr/benchmarks/adapters/no_memory.py`
- `src/shyftr/benchmarks/adapters/mem0_backend.py`
- `scripts/run_memory_benchmark.py`
- `scripts/convert_locomo_standard_fixture.py`
- `scripts/phase11_final_benchmark_report.py`

Gaps:

- no LongMemEval mapper/converter;
- no BEAM mapper/converter;
- no answerer module;
- no judge module;
- no answer-eval aggregate metrics;
- nDCG is documented but not implemented in retrieval metric code;
- answer support coverage and conflict/stale retrieval rate are not implemented;
- no local BM25/vector baseline adapter.

## Optimized Phase 12 recommendation

Phase 12 should be named:

```text
Phase 12: Standard-dataset mapping and runner-owned answer evaluation
```

Recommended ordering:

1. LongMemEval local mapping and conversion scaffolding.
2. Standard-dataset run-case manifest shape for per-question haystack isolation.
3. Deterministic runner-owned answer/judge scaffolding on committed fixtures.
4. Retrieval metric completion, including nDCG and support coverage.
5. BEAM local subset mapping, without large-bucket runs.
6. Optional LLM judge and local scaling runs only after deterministic surfaces are green.
7. Phase 12 closeout report that separates fixture answer-eval, LongMemEval mapping readiness, BEAM mapping readiness, and not-yet-run standard-dataset claims.

Why this is best:

- LongMemEval is the next most useful external benchmark family and the easiest safe mapping target.
- Per-question haystack isolation forces ShyftR to solve the right runner shape before full benchmark claims.
- Deterministic answer-eval should land before any LLM judge so results stay reproducible and cheap.
- BEAM is valuable but should follow LongMemEval because it stresses scale and schema breadth.
- This ordering turns Phase 11's report posture into a stronger benchmark story without jumping into expensive or over-claimed runs.

## Phase 12 first implementation slice

The first slice should be `P12-1: LongMemEval local mapping scaffold`.

Create:

- `src/shyftr/benchmarks/longmemeval_standard.py`
- `scripts/convert_longmemeval_standard_fixture.py`
- `tests/test_benchmark_longmemeval_standard_mapping.py`
- `docs/benchmarks/p12-1-longmemeval-mapping.md`

Modify:

- `src/shyftr/benchmarks/fixture.py`
- `scripts/run_memory_benchmark.py`
- `docs/benchmarks/README.md`

Stop boundary:

- no automatic dataset download;
- no full LongMemEval run;
- no answer/judge implementation in P12-1;
- no BEAM mapping in P12-1;
- no broad benchmark claims.

## References to preserve in the plan

- Phase 11 closeout: `2026-05-17-shyftr-phase-11-final-closeout.md`
- Phase 11 final HTML: `docs/benchmarks/phase11-final-benchmark-report.html`
- Phase 11 final JSON: `docs/benchmarks/phase11-final-benchmark-report.json`
- Existing LOCOMO mapping pattern: `src/shyftr/benchmarks/locomo_standard.py`
- Existing conversion helper pattern: `scripts/convert_locomo_standard_fixture.py`
- Existing mapping tests: `tests/test_benchmark_locomo_standard_mapping.py`
