from __future__ import annotations

import json
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_phase12_report(repo_root: Path) -> dict:
    fixture_report = repo_root / "reports" / "benchmarks" / "phase12_locomo_mini_answer_eval.json"
    report = _load(fixture_report) if fixture_report.exists() else {}
    backend_results = report.get("backend_results", [])
    return {
        "schema_version": "shyftr-phase12-final-report/v0",
        "phase": "Phase 12: Standard-dataset mapping and runner-owned answer evaluation",
        "fixture_reports": [str(fixture_report.relative_to(repo_root))] if fixture_report.exists() else [],
        "retrieval_summary": {
            r.get("backend_name", "unknown"): r.get("metrics", {}).get("retrieval", {}) for r in backend_results
        },
        "answer_eval_summary": {
            r.get("backend_name", "unknown"): r.get("metrics", {}).get("answer_eval", {}) for r in backend_results
        },
        "mapping_readiness": {
            "longmemeval_standard": "local-path/private-by-default mapper, guarded converter, case manifest, no download",
            "beam_standard": "local-path/private-by-default subset mapper, guarded converter, manifest, no download",
        },
        "optional_judge": "design-gated; no credentials or paid API calls required",
        "claims_allowed": [
            "Fixture-level retrieval and deterministic answer-eval reports are reproducible locally.",
            "LongMemEval and BEAM local mapping scaffolds are ready for operator-provided files.",
        ],
        "claims_not_allowed": [
            "No full LongMemEval, BEAM, or LOCOMO standard-dataset performance claim is made.",
            "No broad superiority or production-hosted claim is supported by Phase 12 fixture outputs.",
            "No optional LLM judge result is claimed.",
        ],
    }


def write_html(report: dict, path: Path) -> None:
    rows = []
    for key, value in report.items():
        rows.append(f"<tr><th>{key}</th><td><pre>{json.dumps(value, indent=2, sort_keys=True)}</pre></td></tr>")
    html = """<!doctype html>
<html><head><meta charset='utf-8'><title>ShyftR Phase 12 benchmark report</title>
<style>body{font-family:Inter,system-ui,sans-serif;margin:2rem;line-height:1.45}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:0.75rem;vertical-align:top}th{width:16rem;background:#f6f7f8;text-align:left}pre{white-space:pre-wrap;margin:0}</style></head>
<body><h1>ShyftR Phase 12 benchmark report</h1><p>Claim-limited fixture and mapping-readiness closeout. No dataset downloads or paid API calls.</p><table>""" + "\n".join(rows) + "</table></body></html>\n"
    path.write_text(html, encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report = build_phase12_report(repo_root)
    json_path = repo_root / "docs" / "benchmarks" / "phase12-final-benchmark-report.json"
    html_path = repo_root / "docs" / "benchmarks" / "phase12-final-benchmark-report.html"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_html(report, html_path)
    print(str(json_path))
    print(str(html_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
