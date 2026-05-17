# ShyftR Phase 12 handoff packet

Date: 2026-05-18
Repo: `/Users/stefan/ShyftR`
Starting commit: `bda4817884f3605bed30e9480563df7b6348bc56`
Status: superseded by `2026-05-18-shyftr-phase-12-final-closeout.md` after local Phase 12 completion

## Current truth

Phase 11 is complete, pushed, and CI-green. The final Phase 11 closeout is:

```text
2026-05-17-shyftr-phase-11-final-closeout.md
```

Phase 12 has now been researched and planned. The next implementation phase is:

```text
Phase 12: Standard-dataset mapping and runner-owned answer evaluation
```

Phase 12 should begin with LongMemEval local mapping, not answer-eval or BEAM. Reason: LongMemEval is the safest high-value external benchmark family to add next, with cleaner licensing than some alternatives, smaller operational risk than BEAM, and a schema that exposes the per-question isolation problem ShyftR must solve before standard-dataset claims.

## Canonical Phase 12 artifacts

Read in this order:

1. `2026-05-17-shyftr-phase-11-final-closeout.md`
2. `2026-05-18-shyftr-phase-12-deep-research.md`
3. `2026-05-18-shyftr-phase-12-standard-dataset-answer-eval-tranched-plan.md`
4. `docs/benchmarks/README.md`
5. `docs/benchmarks/methodology.md`
6. `docs/benchmarks/report-schema.md`
7. `src/shyftr/benchmarks/locomo_standard.py`
8. `scripts/convert_locomo_standard_fixture.py`
9. `tests/test_benchmark_locomo_standard_mapping.py`

## Immediate continuation point

Start P12-1:

```text
LongMemEval local mapping scaffold
```

Create the LongMemEval analogue of the existing LOCOMO-standard mapping/conversion pattern.

## P12-1 exact objective

Add local-path/private-by-default LongMemEval mapping and conversion support.

Required new files:

```text
src/shyftr/benchmarks/longmemeval_standard.py
scripts/convert_longmemeval_standard_fixture.py
tests/test_benchmark_longmemeval_standard_mapping.py
docs/benchmarks/p12-1-longmemeval-mapping.md
```

Required modified files:

```text
src/shyftr/benchmarks/fixture.py
scripts/run_memory_benchmark.py
docs/benchmarks/README.md
```

## P12-1 accepted local input shape

A tiny normalized LongMemEval-style test payload is enough for the first tranche. It should support:

```json
{
  "dataset_version": "local-schema-smoke",
  "split": "longmemeval-standard-smoke",
  "contains_private_data": false,
  "cases": [
    {
      "question_id": "q-1",
      "question_type": "single-session-user",
      "question": "Where did the user put the blue notebook?",
      "answer": "on the kitchen shelf",
      "question_date": "2026-01-02",
      "haystack_session_ids": ["session-1"],
      "haystack_dates": ["2026-01-01"],
      "haystack_sessions": [
        [
          {"role": "user", "content": "I keep the blue notebook on the kitchen shelf.", "date": "2026-01-01"},
          {"role": "assistant", "content": "Noted.", "date": "2026-01-01"}
        ]
      ]
    }
  ]
}
```

The mapper may accept the top-level array form too, but it does not need to support every upstream variant in the first tranche. Prefer a conservative normalized contract over overfitted parsing.

## P12-1 tests to write first

```text
test_longmemeval_standard_payload_maps_to_fixture_contract
test_longmemeval_standard_loader_rejects_private_by_default
test_resolver_loads_longmemeval_standard_format_from_explicit_path
test_longmemeval_standard_name_requires_explicit_path
test_converter_writes_guarded_public_fixture
test_converter_rejects_private_input_without_override
test_converter_rejects_output_outside_guarded_dirs
```

Follow the LOCOMO test style in:

```text
tests/test_benchmark_locomo_standard_mapping.py
```

## P12-1 implementation notes

Mirror these existing files:

```text
src/shyftr/benchmarks/locomo_standard.py
scripts/convert_locomo_standard_fixture.py
```

Important details:

- default `contains_private_data` to true;
- use deterministic generated message ids if upstream messages do not provide ids;
- preserve question type in `BenchmarkQuestion.question_type`;
- preserve question date / session ids in evaluation notes or metadata;
- write manifest sidecars with SHA-256 digests and counts;
- output only under `artifacts/`, `reports/`, or `tmp/`;
- require `.json` output;
- reject private input without explicit override;
- require `--public-output` for public-safe converted fixtures.

## P12-1 forbidden side effects

Do not:

- download LongMemEval automatically;
- commit converted third-party dataset files;
- run the full LongMemEval dataset;
- add answerer/judge logic;
- add BEAM mapping;
- make benchmark performance claims;
- use credentials or paid APIs.

## Focused verification for P12-1

```bash
cd /Users/stefan/ShyftR
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_longmemeval_standard_mapping.py
PYTHONPATH=.:src pytest -q tests/test_benchmark_locomo_standard_mapping.py tests/test_benchmark_locomo_mini_fixture.py
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

Then run the full suite before commit:

```bash
PYTHONPATH=.:src pytest -q
```

## Expected P12-1 closeout

Create a tranche closeout before commit:

```text
2026-05-18-shyftr-phase-12-p12-1-longmemeval-mapping-closeout.md
```

It should state:

- exactly what was mapped;
- what input shape is supported;
- whether any dataset was downloaded; expected answer: no;
- whether any full LongMemEval run is claimed; expected answer: no;
- focused and full verification results;
- next tranche recommendation, likely P12-2 case-manifest/per-question isolation contract.

## Human input requirement

None for P12-1 if using only synthetic local test payloads.

Human approval is required before:

- downloading full LongMemEval;
- downloading BEAM;
- using LLM/API credentials;
- publishing any converted benchmark artifact built from third-party data;
- changing from fixture-level claims to full standard-dataset result claims.

## Resume checklist

1. `cd /Users/stefan/ShyftR`
2. `git status --short --branch`
3. Read this handoff and the Phase 12 plan.
4. Run `PYTHONPATH=.:src pytest -q tests/test_benchmark_locomo_standard_mapping.py` to confirm the template pattern is still green.
5. Start by creating `tests/test_benchmark_longmemeval_standard_mapping.py` with the seven RED tests listed above.
6. Implement `src/shyftr/benchmarks/longmemeval_standard.py` until mapper/loader tests pass.
7. Implement `scripts/convert_longmemeval_standard_fixture.py` until converter tests pass.
8. Add dispatch support in `fixture.py` and `run_memory_benchmark.py`.
9. Update docs and write the closeout.
10. Run focused/full gates, commit, push, and verify CI.
