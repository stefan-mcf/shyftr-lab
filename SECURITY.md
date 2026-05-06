# Security Policy

## Status

ShyftR is a stable local-first project. It is not a hosted service and does not claim multi-tenant production hardening.

## Reporting

Please report vulnerabilities through GitHub private vulnerability reporting if enabled, or open a minimal public issue that describes the affected surface without including secrets, private cells, credentials, or sensitive ledgers.

## Local data boundary

cells may contain sensitive memory. Do not upload real cell ledgers, `.env` files, API tokens, private keys, or operator screenshots in issues or pull requests. Use synthetic reproductions whenever possible.
