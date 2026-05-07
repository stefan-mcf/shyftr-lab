# Evolution examples

These examples describe synthetic scenarios for the local memory-evolution surfaces.

1. Oversized candidate split proposal.
2. Exact duplicate consolidation proposal.
3. Similar-but-not-same memory remains separate or high-risk.
4. Repeated feedback supersedes or deprecates old memory only through a proposal.
5. Forget/deprecate/redact excludes memory only after accepted review.
6. Malicious evidence cannot force auto-apply.
7. Scanner rate limiting prevents proposal storms.

Run the public-safe proof:

```bash
PYTHONPATH=src python -m compileall -q src scripts examples
```
