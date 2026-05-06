# Adapter SDK guide

Status: Phase 8 public-safe adapter SDK guide for stable local-first release users.

ShyftR adapters bring external evidence into a cell without giving the external runtime authority over canonical memory truth. Adapters discover local/exported source material, preserve provenance, and let ShyftR run the same review-gated evidence -> candidate -> memory -> pack -> feedback loop.

## Trust model

Installing a Python adapter plugin is equivalent to installing any Python package: its code can execute locally when the plugin is loaded. Only install adapters from trusted packages. Public ShyftR adapters should prefer local exports and synthetic fixtures over live service credentials.

## Entry point

Third-party packages advertise metadata through the `shyftr.adapters` entry-point group. The metadata includes:

- `name`
- `version`
- `supported_input_kinds`
- `capabilities`
- `adapter_sdk_version`
- `config_schema_version`
- `adapter_class`

The built-in file adapter remains available without optional plugins.

## Implement an input adapter

Implement the `adapter protocol` protocol from `shyftr.integrations.protocols`:

1. `discover_sources()` returns `ExternalSourceRef` records.
2. `read_source(ref)` returns a `SourcePayload` and preserves the external ref.
3. `source_metadata(ref)` returns lightweight metadata without ingesting.

A minimal working template is available at `src/shyftr/integrations/template_adapter.py`.

## Validate an adapter

Use the public harness before publishing an adapter:

```python
from shyftr.integrations.template_adapter import MarkdownFolderTemplateAdapter
from shyftr.integrations.test_harness import AdapterTestHarness

adapter = MarkdownFolderTemplateAdapter("./exported-notes")
result = AdapterTestHarness(adapter).run(require_sources=True)
assert result.status == "ok", result.to_dict()
```

## Public/private split

Good public examples read local Markdown, JSONL runtime logs, exported issue data, or exported chat transcripts. Do not ship examples that require real API tokens, customer data, employer data, regulated data, hosted ShyftR services, or private-core scoring/ranking/compaction.
