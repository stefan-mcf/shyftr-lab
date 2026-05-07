from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

DEFAULT_TOLERANCE = 0.0
TOLERANCES = {
    "average_useful_memory_inclusion_rate": 0.0,
    "average_stale_memory_inclusion_rate": 0.0,
    "average_harmful_memory_inclusion_rate": 0.0,
    "average_ignored_memory_inclusion_rate": 0.0,
    "average_missing_memory_rate": 0.0,
    "average_resume_state_score": 0.0,
    "total_raw_items": 0.0,
}


def _read(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fixture_index(summary: Mapping[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    index: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for mode, results in dict(summary.get("fixture_results") or {}).items():
        index[mode] = {result["fixture_id"]: result for result in results}
    return index


def _schema_check(baseline: Mapping[str, Any], candidate: Mapping[str, Any]) -> List[str]:
    failures: List[str] = []
    if baseline.get("output_schema_version") != candidate.get("output_schema_version"):
        failures.append(
            f"schema drift: baseline={baseline.get('output_schema_version')} candidate={candidate.get('output_schema_version')}"
        )
    if set((baseline.get("mode_summaries") or {}).keys()) != set((candidate.get("mode_summaries") or {}).keys()):
        failures.append("mode_summaries keys differ")
    if set((baseline.get("fixture_results") or {}).keys()) != set((candidate.get("fixture_results") or {}).keys()):
        failures.append("fixture_results keys differ")
    return failures


def compare(baseline: Mapping[str, Any], candidate: Mapping[str, Any]) -> Dict[str, Any]:
    failures = _schema_check(baseline, candidate)
    improvements: List[str] = []
    regressions: List[str] = []
    neutral: List[str] = []

    for mode, baseline_summary in dict(baseline.get("mode_summaries") or {}).items():
        candidate_summary = dict(candidate.get("mode_summaries") or {}).get(mode, {})
        for key, baseline_value in baseline_summary.items():
            candidate_value = candidate_summary.get(key)
            tolerance = TOLERANCES.get(key, DEFAULT_TOLERANCE)
            delta = round(float(candidate_value) - float(baseline_value), 6)
            if abs(delta) <= tolerance:
                neutral.append(f"{mode}.{key}: stable ({baseline_value} -> {candidate_value})")
            elif key in {"average_useful_memory_inclusion_rate", "average_resume_state_score"}:
                (improvements if delta > 0 else regressions).append(f"{mode}.{key}: {baseline_value} -> {candidate_value} (delta {delta:+})")
            else:
                (improvements if delta < 0 else regressions).append(f"{mode}.{key}: {baseline_value} -> {candidate_value} (delta {delta:+})")

    baseline_index = _fixture_index(baseline)
    candidate_index = _fixture_index(candidate)
    for mode, fixtures in baseline_index.items():
        for fixture_id, baseline_result in fixtures.items():
            candidate_result = candidate_index.get(mode, {}).get(fixture_id)
            if candidate_result is None:
                failures.append(f"missing fixture result: {mode}.{fixture_id}")
                continue
            if baseline_result.get("expectation_evaluation", {}).get("pass") and not candidate_result.get("expectation_evaluation", {}).get("pass"):
                regressions.append(f"{mode}.{fixture_id}: expectation evaluation regressed from pass to fail")
            elif (not baseline_result.get("expectation_evaluation", {}).get("pass")) and candidate_result.get("expectation_evaluation", {}).get("pass"):
                improvements.append(f"{mode}.{fixture_id}: expectation evaluation improved from fail to pass")

    status = "pass" if not failures and not regressions else "fail"
    return {
        "status": status,
        "schema_failures": failures,
        "improvements": improvements,
        "regressions": regressions,
        "neutral": neutral,
    }


def render_markdown(report: Mapping[str, Any], baseline_path: Path, candidate_path: Path) -> str:
    lines = [
        "# Current-state baseline comparison",
        "",
        f"- baseline: `{baseline_path}`",
        f"- candidate: `{candidate_path}`",
        f"- status: **{report['status'].upper()}**",
        "",
    ]
    for heading, key in [("Schema failures", "schema_failures"), ("Improvements", "improvements"), ("Regressions", "regressions"), ("Neutral deltas", "neutral")]:
        lines.append(f"## {heading}")
        values = list(report.get(key, []))
        if not values:
            lines.append("- none")
        else:
            lines.extend([f"- {value}" for value in values])
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two ShyftR current-state baseline summaries.")
    parser.add_argument("baseline_json")
    parser.add_argument("candidate_json")
    parser.add_argument("--markdown-out", default=None)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    baseline_path = Path(args.baseline_json).resolve()
    candidate_path = Path(args.candidate_json).resolve()
    report = compare(_read(baseline_path), _read(candidate_path))
    markdown = render_markdown(report, baseline_path, candidate_path)
    if args.markdown_out:
        out = Path(args.markdown_out).resolve()
        out.write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
