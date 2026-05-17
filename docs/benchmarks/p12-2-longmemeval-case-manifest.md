# P12-2 LongMemEval case manifest and per-question grouping contract

Status: implemented as local mapping/conversion metadata. No LongMemEval dataset is downloaded or run.

The LongMemEval mapper preserves each question case as a per-question grouping marker. Converted fixtures carry per-question metadata through conversation/message metadata and question evaluation notes. The conversion sidecar includes a nested case manifest with:

- case count;
- session count;
- message count;
- question-type counts;
- input and output SHA-256 digests;
- private/public posture;
- an explicit claim limit.

Future full LongMemEval runs must reset backend state per case unless a separate experiment explicitly declares shared warm memory. The current Phase 12 contract is mapping readiness only.
