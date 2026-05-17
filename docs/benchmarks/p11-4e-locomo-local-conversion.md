# P11-4e: LOCOMO local conversion helper

Status: local-only helper for operator-provided files. No automatic dataset download.

This tranche adds a guarded conversion script for local normalized LOCOMO-style files after the P11-4d mapping layer.

## Command

```bash
PYTHONPATH=.:src python scripts/convert_locomo_standard_fixture.py \
  --input /path/to/local/locomo-standard.json \
  --output artifacts/benchmarks/locomo_standard_converted.fixture.json \
  --allow-private-input
```

The helper also writes a sidecar manifest by default:

```text
artifacts/benchmarks/locomo_standard_converted.fixture.json.manifest.json
```

The manifest records input/output SHA-256 digests, fixture counts, privacy posture, and the explicit claim limit. Use `--no-manifest` only for scratch debugging.

For a public-safe converted fixture, the input must declare `contains_private_data: false` and the command must use `--public-output`:

```bash
PYTHONPATH=.:src python scripts/convert_locomo_standard_fixture.py \
  --input /path/to/public-safe-normalized-locomo.json \
  --output artifacts/benchmarks/locomo_standard_public.fixture.json \
  --public-output
```

## Write guards

The helper refuses to write outside repo-local:

- `artifacts/`
- `reports/`
- `tmp/`

It also requires `.json` output. This keeps converted files out of committed fixture paths unless an operator deliberately reviews and moves a public-safe result later.

## Input support

Supported input is the same conservative normalized LOCOMO-style shape documented in `docs/benchmarks/p11-4d-locomo-standard-mapping.md`.

The helper also accepts JSONL as local scratch input. JSONL rows are treated as conversations and default to private input unless an operator passes `--allow-private-input`.

## Claim limits

Allowed:

- The script converts operator-provided local normalized LOCOMO-style files into ShyftR benchmark fixture JSON.
- Output is guarded to local artifact/report/temp directories.

Not allowed:

- The script downloads LOCOMO.
- The converted file is automatically public-safe.
- This is a full LOCOMO benchmark run.
- This validates LongMemEval or BEAM.
- This proves benchmark superiority or task-success lift.
