# ShyftR v1 local HTTP API versioning

Status: Phase 8 public-safe API contract note.

The local HTTP service exposes the public integration surface under `/v1`. Unversioned routes remain as compatibility aliases and return deprecation headers. New external integrations should use `/v1/*` paths.

## Version policy

- `/v1` is the first developer-preview API surface.
- Additive response fields may be added within v1.
- Breaking route, method, or required-field changes require a future major path such as `/v2`.
- Compatibility aliases are retained for migration safety and are not evidence for new stable surfaces.

## OpenAPI contract

Generate the committed v1 OpenAPI contract with:

```bash
PYTHONPATH=src python scripts/generate_openapi.py
```

The generated file is `docs/openapi-v1.json`. Contract drift should be reviewed before release-language changes.

## Headers

All local HTTP responses include:

- `X-ShyftR-API-Version: v1`

Unversioned compatibility aliases additionally include:

- `Deprecation: true`
- `Link: </v1>; rel="successor-version"`

## Safety posture

The v1 API is local-first and local-reviewed oriented. It is not a hosted SaaS API, multi-tenant API, or production service safety boundary. Canonical truth remains append-only cell ledgers; the service is a local adapter surface.
