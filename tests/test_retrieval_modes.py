from pathlib import Path

from shyftr.ledger import append_jsonl
from shyftr.layout import init_cell
from shyftr.pack import LoadoutTaskInput, assemble_loadout
from shyftr.retrieval_modes import apply_retrieval_mode_to_task, retrieval_mode_config, validate_retrieval_mode


def _seed(cell: Path) -> None:
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "strong", "cell_id": "core", "statement": "Strong deploy checklist", "confidence": 0.9, "kind": "workflow", "status": "approved", "source_fragment_ids": ["c1"]})
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "weak", "cell_id": "core", "statement": "Weak deploy idea", "confidence": 0.2, "kind": "workflow", "status": "approved", "source_fragment_ids": ["c1"]})
    append_jsonl(cell / "doctrine" / "approved.jsonl", {"doctrine_id": "rule-1", "cell_id": "core", "statement": "Always review policy before mutation", "review_status": "approved"})


def test_default_mode_preserves_balanced_behavior(tmp_path):
    cell = init_cell(tmp_path, "core")
    _seed(cell)
    pack = assemble_loadout(LoadoutTaskInput(cell_path=str(cell), query="deploy", task_id="t", dry_run=True))
    assert pack.retrieval_log.score_traces
    assert validate_retrieval_mode(None) == "balanced"


def test_conservative_mode_excludes_weak_memory(tmp_path):
    cell = init_cell(tmp_path, "core")
    _seed(cell)
    pack = assemble_loadout(LoadoutTaskInput(cell_path=str(cell), query="deploy", task_id="t", retrieval_mode="conservative", dry_run=True))
    ids = [item.item_id for item in pack.items]
    assert "weak" not in ids
    assert "weak" in pack.retrieval_log.suppressed_ids


def test_rule_only_mode_returns_rules_without_memory(tmp_path):
    cell = init_cell(tmp_path, "core")
    _seed(cell)
    pack = assemble_loadout(LoadoutTaskInput(cell_path=str(cell), query="policy", task_id="t", retrieval_mode="rule_only", dry_run=True))
    assert [item.trust_tier for item in pack.items] == ["doctrine"]


def test_all_frontier_retrieval_modes_have_public_safe_effects(tmp_path):
    cell = init_cell(tmp_path, "core")
    base = LoadoutTaskInput(cell_path=str(cell), query="deploy", task_id="t", max_items=20, max_tokens=5000, dry_run=True)

    exploratory = apply_retrieval_mode_to_task(base.__class__.from_dict({**base.to_dict(), "retrieval_mode": "exploratory"}))
    assert exploratory is not base
    assert exploratory.include_fragments is True
    assert exploratory.caution_max_items == retrieval_mode_config("exploratory")["caution_max_items"]

    risk_averse = apply_retrieval_mode_to_task(base.__class__.from_dict({**base.to_dict(), "retrieval_mode": "risk_averse"}))
    assert risk_averse.caution_max_items == retrieval_mode_config("risk_averse")["caution_max_items"]

    audit = apply_retrieval_mode_to_task(base.__class__.from_dict({**base.to_dict(), "retrieval_mode": "audit"}))
    assert audit.audit_mode is True
    assert audit.include_fragments is True

    low_latency = apply_retrieval_mode_to_task(base.__class__.from_dict({**base.to_dict(), "retrieval_mode": "low_latency"}))
    assert low_latency.max_items == 5
    assert low_latency.max_tokens == 1200
    assert base.max_items == 20
    assert base.max_tokens == 5000
