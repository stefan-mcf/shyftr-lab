# ShyftR release readiness

Status: stable local-first public release.

ShyftR is public so operators and collaborators can clone it, run local synthetic examples, inspect the architecture, and use reviewed local cells with operator-approved non-sensitive data. Hosted platform operation, multi-tenant deployment, package publication, and unreviewed sensitive memory remain outside the current public release.

## Who should use this release

Good release scope:

- operators or collaborators comfortable with Python virtual environments and terminal output;
- synthetic or non-sensitive data;
- exact commands, platform details, and error output recorded when relevant;
- concept clarity, install friction, CLI/example reliability, and local console feel reviewed.

Needs separate approval:

- non-technical packaged desktop distribution;
- hosted or multi-tenant service operation;
- private/customer/regulated memory;
- package publication, release tags, or support commitments.

## Release gate

After installing from the public repo, run:

```bash
bash scripts/release_gate.sh
```

Expected final line:

```text
SHYFTR_RELEASE_READY
```

The gate uses synthetic data by default. It checks:

- CLI import/help smoke;
- public release/readiness posture;
- Python tests;
- deterministic local lifecycle example;
- synthetic replacement-readiness replay;
- diagnostic logging summary;
- optional console build and production-dependency audit when npm is available.

If the gate fails, capture the full terminal output, OS, Python version, Node/npm version if relevant, and whether the failure occurred before or after dependency installation for operator review.

## Data policy for release use

Use:

- synthetic examples under `examples/`;
- throwaway local cells;
- non-sensitive notes intentionally created for testing;
- operator-approved local data only after reviewing `SECURITY.md`.

Do not use:

- API keys, private keys, `.env` files, or tokens;
- customer, employer, regulated, or confidential data;
- production memory ledgers without a separate operator review;
- private operator workflows or screenshots containing secrets.

## What feedback is useful

For operator review, record:

- reviewer label;
- exact commit tested from `git rev-parse HEAD`;
- OS and version;
- Python version;
- Node/npm versions if the console build runs;
- whether `scripts/release_gate.sh` finished with `SHYFTR_RELEASE_READY`;
- install friction or full public-safe error output;
- whether the lifecycle demo made the pack -> feedback loop understandable;
- terminology or concept-clarity feedback;
- anything that would block a small local deployment.

## Current boundary

Release readiness means the local proof path is healthy enough for operator-run use with synthetic or approved non-sensitive data. It does not authorize hosted service operation, package publication, support commitments, or broad managed-memory replacement claims. Bounded-domain primary memory requires explicit operator approval after replay/readiness evidence and fallback/archive review.
