from __future__ import annotations

import json
from pathlib import Path

from scripts.phase11_final_benchmark_report import generate_phase11_report


def test_phase11_final_report_renders_html_and_json(tmp_path: Path) -> None:
    report_path = tmp_path / "synthetic_report.json"
    report_path.write_text(
        json.dumps(
            {
                "dataset": {"name": "synthetic-mini"},
                "backend_results": [
                    {
                        "backend_name": "shyftr-local-cell",
                        "status": "ok",
                        "metrics": {"retrieval": {"recall_at_k": 1.0, "precision_at_k": 0.5, "mrr": 1.0}},
                        "control_audit": {"provenance_coverage": 1.0},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_html = tmp_path / "phase11.html"
    output_json = tmp_path / "phase11.json"

    summary = generate_phase11_report(
        report_paths=[report_path],
        output_html=output_html,
        output_json=output_json,
        git_sha="abc123",
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    html_text = output_html.read_text(encoding="utf-8")
    assert summary["schema_version"] == "shyftr-phase11-final-benchmark-closeout/v0"
    assert payload["git_sha"] == "abc123"
    assert payload["backend_rows"][0]["backend"] == "shyftr-local-cell"
    assert "Governed memory, measured without myth" in html_text
    assert "synthetic-mini" in html_text
    assert "LOCOMO" in html_text
