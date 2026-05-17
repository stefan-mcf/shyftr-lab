# ShyftR Phase 11 P11-4d closeout: LOCOMO-standard mapping layer

Status: implemented and locally verified.

## Scope

P11-4d starts the first standard-dataset mapping layer without downloading or committing full third-party datasets.

Implemented:

- `src/shyftr/benchmarks/locomo_standard.py` maps a normalized LOCOMO-style local JSON payload into the Phase 11 `BenchmarkFixture` contract.
- `--fixture locomo-standard` is accepted by the CLI, but requires an explicit local `--fixture-path`.
- `--fixture-format locomo-standard` selects the mapper for explicit local paths.
- LOCOMO-standard input defaults to private unless `contains_private_data: false` is declared.
- Private-marked input is rejected unless `--allow-private-fixture` is passed.
- Focused tests cover mapping, resolver wiring, explicit path requirement, and private-data rejection.
- Docs describe the normalized input shape and claim boundaries.

Not implemented:

- No full LOCOMO download.
- No LongMemEval or BEAM mapping.
- No broad benchmark or superiority claims.
- No backend-owned answering.
- No automatic dataset fetching.

## Verification

Smoke verification completed:

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_locomo_standard_mapping.py
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture locomo-standard \
  --fixture-path <public-safe-local-json> \
  --fixture-format locomo-standard \
  --run-id p11-4d-cli-smoke \
  --output artifacts/benchmarks/p11_4d_cli_smoke.json \
  --top-k 1
```

Observed smoke properties:

- focused LOCOMO-standard mapping tests: `4 passed`
- CLI mapped dataset name: `locomo-standard`
- CLI mapped split: `locomo-standard-cli-smoke`

Full gate verification completed before commit:

```bash
PYTHONPATH=.:src python -m compileall -q src scripts examples
PYTHONPATH=.:src pytest -q tests/test_benchmark_adapter_contract.py tests/test_benchmark_locomo_mini_fixture.py tests/test_benchmark_locomo_standard_mapping.py
PYTHONPATH=.:src pytest -q
python scripts/terminology_inventory.py --fail-on-public-stale
python scripts/terminology_inventory.py --fail-on-capitalized-prose
python scripts/public_readiness_check.py
git diff --check
```

Result:

- focused benchmark tests: `14 passed`
- full suite: `1109 passed, 40 warnings`
- terminology public-stale check: pass
- terminology capitalized prose check: pass
- public readiness check: pass
- git diff whitespace check: pass

## Next tranche

P11-4e should either add a local conversion helper for real downloaded LOCOMO files with fixture-output write guards, or begin LongMemEval mapping documentation. Keep full dataset downloads operator-triggered and local-only.
