# Metrics contract

Schema version: `current-state-baseline.v1`

Phase 2 note: the baseline schema version stays stable, but Mode B and Mode C now permit typed carry-state/checkpoint and resume-validation extras alongside the required shared fields.

## Modes

- `durable`: current durable-memory-only path through loadout assembly.
- `carry`: current durable + carry/continuity path.
- `live`: current durable + carry/continuity + live-context path.
- `behavior`: raw pack/loadout behavior capture and normalization.

## Per-run metadata

Required top-level summary fields:
- `run_id`
- `git_sha`
- `fixture_count`
- `fixtures_included`
- `mode`
- `mode_summaries`
- `fixture_results`
- `behavior`
- `known_limitations`
- `output_schema_version`

## Fixture result record

Required fields for `durable`, `carry`, and `live` records:
- `fixture_id`
- `mode`
- `surfaced_ids`
- `expected_useful_ids`
- `expected_required_ids`
- `matched_useful_count`
- `stale_count`
- `harmful_count`
- `ignored_count`
- `missing_required_count`
- `useful_memory_inclusion_rate`
- `stale_memory_inclusion_rate`
- `harmful_memory_inclusion_rate`
- `ignored_memory_inclusion_rate`
- `missing_memory_rate`
- `duplicate_or_redundant_inclusion_rate`
- `duplicate_count`
- `redundant_ids`
- `raw_item_count`
- `total_tokens`
- `resume_state_score`
- `preserved_constraint_rate`
- `preserved_decision_rate`
- `preserved_artifact_ref_rate`
- `preserved_open_loop_rate`
- `notes`
- `expectation_evaluation`

Mode-specific extras may be added, but the shared fields above must remain present.

## Aggregate summary contract

Each mode summary contains:
- `fixture_count`
- `average_useful_memory_inclusion_rate`
- `average_stale_memory_inclusion_rate`
- `average_harmful_memory_inclusion_rate`
- `average_ignored_memory_inclusion_rate`
- `average_missing_memory_rate`
- `average_resume_state_score`
- `total_raw_items`

## Metric definitions

### useful_memory_inclusion_rate
Fraction of labeled useful ids surfaced by the current mode.

### stale_memory_inclusion_rate
Fraction of labeled stale ids incorrectly surfaced.

### harmful_memory_inclusion_rate
Fraction of labeled harmful ids incorrectly surfaced.

### ignored_memory_inclusion_rate
Fraction of labeled ignored ids surfaced.

### missing_memory_rate
Fraction of required ids that were absent.

### duplicate_or_redundant_inclusion_rate
Share of surfaced items that were duplicated or unlabeled/redundant.

### resume_state_score
Combined score over required inclusion plus excluded-id suppression for the fixture's expected resume state.

### preserved_constraint_rate
Fraction of expected constraint ids preserved.

### preserved_decision_rate
Fraction of expected decision ids preserved.

### preserved_artifact_ref_rate
Fraction of expected artifact-ref ids preserved.

### preserved_open_loop_rate
Fraction of expected open-question/open-loop ids preserved.

## Fixture doctrine

Fixtures must be:
- synthetic;
- deterministic;
- bounded;
- hand-labeled;
- human-readable.

Each fixture must separate:
- durable memories;
- continuity observations/feedback seeds;
- live-context entries;
- expected useful/stale/harmful/ignored/required ids.

## Scoring rules

- Preserve raw current behavior first.
- Normalize only at the scoring layer.
- If current behavior cannot honestly support a score, emit a limitation instead of inventing a success metric.
- Exact equality is expected for stable structural metrics.
- Comparator tolerances may be configured per metric later, but schema drift must always fail loudly.

## Phase 2 extras

Typical optional extras now include:
- `carry_state_present`
- `carry_candidate_count`
- `memory_candidate_count`
- `carry_state_checkpoint_count`
- `carry_state_checkpoint_tokens`
- `checkpoint_total_items`
- `checkpoint_total_tokens`
- `resume_validation`

These enrich regression analysis but do not replace the required shared fields above.

## Explicit exclusions

- no retrieval redesign;
- no broad benchmark or external-runtime superiority claims.
