# ShyftR Phase 11 P11-4e closeout: LOCOMO local conversion helper

Status: implemented and locally verified.

## Scope

P11-4e adds a local-only conversion helper after the P11-4d mapping layer. It remains operator-triggered and does not download datasets.

Implemented:

- `scripts/convert_locomo_standard_fixture.py` converts local normalized LOCOMO-style JSON/JSONL into ShyftR benchmark fixture JSON.
- Output path guard permits only repo-local `artifacts/`, `reports/`, or `tmp/` paths.
- Output must be `.json`.
- Private or unknown input requires `--allow-private-input`.
- Public-safe output requires `--public-output` and `contains_private_data: false`.
- Focused tests cover public conversion, private override, and output guard rejection.
- Docs describe the helper, input posture, and claim limits.

Not implemented:

- No automatic LOCOMO download.
- No full LOCOMO execution.
- No LongMemEval or BEAM conversion.
- No broad benchmark or superiority claims.
- No generated converted fixture is committed.

## Verification

Smoke verification completed:

```bash
PYTHONPATH=.:src pytest -q tests/test_benchmark_locomo_standard_mapping.py
PYTHONPATH=.:src python scripts/convert_locomo_standard_fixture.py \
  --input <public-safe-local-json> \
  --output artifacts/benchmarks/p11_4e_convert_smoke.fixture.json \
  --public-output
```

Observed smoke properties:

- LOCOMO-standard mapping/conversion tests: `7 passed`
- converter wrote under `artifacts/benchmarks/`
- converted dataset name: `locomo-standard`
- converted fixture id: `locomo-convert-smoke`

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

- focused benchmark tests: `17 passed`
- full suite: `1112 passed, 40 warnings`
- terminology public-stale check: pass
- terminology capitalized prose check: pass
- public readiness check: pass
- git diff whitespace check: pass

## Next tranche

P11-4f should either add a fixture manifest/digest step for converted local files or begin LongMemEval mapping documentation. Keep all third-party dataset files local-only unless a specific public-safe sample is reviewed separately.
