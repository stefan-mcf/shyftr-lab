# P12-7 optional LLM judge and local scaling design gate

Status: design-gated. Deterministic runner-owned answer evaluation is implemented; optional LLM judging remains disabled by default.

Required decisions before any optional LLM judge code is enabled:

1. Provider interface: must be an explicit local operator choice, never inferred from ambient credentials.
2. Run metadata: report model name, prompt version, temperature, token counts, cost estimate, and skip reason when unavailable.
3. Credential posture: missing credentials must produce a skipped result, not a failed benchmark or silent fallback.
4. Output posture: private scaling outputs must stay under guarded local directories and must not be committed unless public-safety has been explicitly reviewed.
5. Claim posture: reports must say whether the judge is deterministic, LLM-assisted, or skipped, and must not turn fixture-level answer evaluation into standard-dataset answer-quality claims.

No credentials, paid API calls, or large local runs are required for Phase 12 closeout.
