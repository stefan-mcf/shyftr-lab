# P12-6 BEAM local subset mapping

Status: implemented as a local subset scaffold. No BEAM dataset is downloaded or run.

`scripts/convert_beam_standard_fixture.py` accepts operator-provided normalized BEAM-style JSON/JSONL and writes guarded ShyftR benchmark fixtures only under `artifacts/`, `reports/`, or `tmp/`. Inputs default to private unless they explicitly declare `contains_private_data: false` and the operator requests `--public-output`.

The mapper preserves the BEAM ability label in `BenchmarkQuestion.question_type`, keeps token-bucket labels when present, and writes a manifest sidecar with case/message counts, ability counts, optional token-bucket counts, SHA-256 digests, privacy posture, and claim limits.

This is a conversion scaffold only. It does not support broad BEAM performance claims or large-bucket runs.
