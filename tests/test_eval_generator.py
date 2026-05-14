from shyftr.ledger import append_jsonl
from shyftr.layout import init_cell
from shyftr.evalgen import export_eval_tasks, generate_eval_tasks


def test_empty_eval_generator_returns_public_safe_evolution_safety_payload(tmp_path):
    cell = init_cell(tmp_path, "core")
    tasks = generate_eval_tasks(cell)
    assert tasks
    assert all(task["task_id"].startswith("evolution-") for task in tasks)
    payload = export_eval_tasks(cell)
    assert payload["status"] == "ok"
    assert payload["total"] == len(tasks)
    assert payload["public_safe"] is True


def test_eval_generator_creates_deterministic_public_safe_tasks(tmp_path):
    cell = init_cell(tmp_path, "core")
    append_jsonl(cell / "ledger" / "outcomes.jsonl", {"outcome_id": "o1", "useful_trace_ids": ["m1"], "harmful_trace_ids": ["m2"], "missing_memory": ["note"]})
    append_jsonl(cell / "traces" / "approved.jsonl", {"trace_id": "m1", "cell_id": "core", "statement": "High value deploy memory", "confidence": 0.95, "success_count": 3})
    tasks = generate_eval_tasks(cell)
    assert [task["task_id"] for task in tasks] == sorted(task["task_id"] for task in tasks)
    assert all(task["private_data_allowed"] is False for task in tasks)
    assert any(task["expected_pack_item_ids"] == ["m1"] for task in tasks)
    out = tmp_path / "evals.jsonl"
    payload = export_eval_tasks(cell, out, jsonl=True)
    assert payload["public_safe"] is True
    assert str(tmp_path) not in out.read_text()
