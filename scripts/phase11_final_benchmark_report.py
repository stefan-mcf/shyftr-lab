from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


DATASET_MATRIX = [
    {
        "name": "synthetic-mini",
        "status": "measured fixture",
        "scope": "Contract and adapter smoke benchmark",
        "claim": "Fixture-level retrieval/control behavior only",
    },
    {
        "name": "locomo-mini",
        "status": "measured fixture",
        "scope": "Tiny LOCOMO-shaped public-safe run",
        "claim": "Loader/report/claim-path validation only",
    },
    {
        "name": "locomo-standard",
        "status": "local mapping + conversion scaffold",
        "scope": "Operator-provided normalized local files",
        "claim": "Mapping and guarded conversion readiness only unless a local run report is supplied",
    },
    {
        "name": "LongMemEval",
        "status": "methodology target",
        "scope": "Future local subset mapping",
        "claim": "Not measured in Phase 11 closeout",
    },
    {
        "name": "BEAM",
        "status": "methodology target",
        "scope": "Future large-scale retrieval once local costs are controlled",
        "claim": "Not measured in Phase 11 closeout",
    },
]


PHASES = [
    ("P11-0", "Methodology, adapter contract, fixture/report schemas"),
    ("P11-1", "Fixture-safe runner, ShyftR/no-memory baseline, output guards"),
    ("P11-2", "Optional mem0 OSS comparator with skipped status when unavailable"),
    ("P11-3", "LOCOMO-mini fixture and public-safe report path"),
    ("P11-4a", "Multi-top-k metrics and cost/timeout summaries"),
    ("P11-4b", "Operation timeout and resume controls"),
    ("P11-4c", "Deterministic retry execution and retry accounting"),
    ("P11-4d", "LOCOMO-standard local mapping scaffold"),
    ("P11-4e", "LOCOMO local conversion helper and manifest sidecar"),
    ("P11-final", "Closing report and polished HTML benchmark dossier"),
]


CLAIMS_ALLOWED = [
    "Phase 11 provides a reproducible, public-safe external-memory benchmark track.",
    "Synthetic-mini and LOCOMO-mini fixture reports can compare ShyftR, no-memory, and optional mem0 OSS under one runner contract.",
    "LOCOMO-standard support is local-path, private-by-default mapping/conversion scaffolding unless an operator supplies a public-safe local file and run report.",
    "Reports disclose top-k values, timeout/retry/resume controls, cost/latency summaries, limitations, and claim boundaries.",
]


CLAIMS_NOT_ALLOWED = [
    "No broad ShyftR superiority claim is supported by Phase 11 fixture runs.",
    "No full LOCOMO, LongMemEval, or BEAM result is claimed unless a separate local run report is supplied and reviewed.",
    "No hosted-service, production-managed-memory, or private-core ranking claim is made.",
    "No runner-owned answer-quality result is claimed beyond retrieval/control metrics currently implemented.",
]


def _load_report(path: Path) -> Dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _backend_summary(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    dataset = report.get("dataset") or {}
    for backend in report.get("backend_results") or []:
        metrics = backend.get("metrics") or {}
        retrieval = metrics.get("retrieval") or {}
        control = backend.get("control_audit") or {}
        rows.append(
            {
                "dataset": dataset.get("name", "unknown"),
                "backend": backend.get("backend_name", "unknown"),
                "status": backend.get("status", "unknown"),
                "recall_at_k": retrieval.get("recall_at_k", "not_run"),
                "precision_at_k": retrieval.get("precision_at_k", "not_run"),
                "mrr": retrieval.get("mrr", "not_run"),
                "provenance_coverage": control.get("provenance_coverage", "not_supported"),
            }
        )
    return rows


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return html.escape(str(value))


def _build_summary(reports: Iterable[Dict[str, Any]], *, git_sha: str = "unknown") -> Dict[str, Any]:
    report_list = list(reports)
    return {
        "schema_version": "shyftr-phase11-final-benchmark-closeout/v0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "git_sha": git_sha,
        "phase_status": "complete_with_claim_limits",
        "report_count": len(report_list),
        "datasets": DATASET_MATRIX,
        "tranches": [{"id": ident, "summary": summary} for ident, summary in PHASES],
        "backend_rows": [row for report in report_list for row in _backend_summary(report)],
        "claims_allowed": CLAIMS_ALLOWED,
        "claims_not_allowed": CLAIMS_NOT_ALLOWED,
    }


def _render_html(summary: Dict[str, Any]) -> str:
    backend_rows = summary.get("backend_rows") or []
    measured = len([row for row in backend_rows if row.get("status") == "ok"])
    skipped = len([row for row in backend_rows if row.get("status") == "skipped"])
    failed = len([row for row in backend_rows if row.get("status") == "failed"])

    dataset_cards = "\n".join(
        f"""
        <article class=\"dataset-card\">
          <div class=\"eyebrow\">{html.escape(item['status'])}</div>
          <h3>{html.escape(item['name'])}</h3>
          <p>{html.escape(item['scope'])}</p>
          <span>{html.escape(item['claim'])}</span>
        </article>
        """
        for item in summary.get("datasets") or []
    )
    tranche_rows = "\n".join(
        f"<tr><td>{html.escape(item['id'])}</td><td>{html.escape(item['summary'])}</td><td><b>Complete</b></td></tr>"
        for item in summary.get("tranches") or []
    )
    backend_table = "\n".join(
        f"<tr><td>{html.escape(row['dataset'])}</td><td>{html.escape(row['backend'])}</td><td>{html.escape(row['status'])}</td><td>{_fmt(row['recall_at_k'])}</td><td>{_fmt(row['precision_at_k'])}</td><td>{_fmt(row['mrr'])}</td><td>{_fmt(row['provenance_coverage'])}</td></tr>"
        for row in backend_rows
    ) or "<tr><td colspan=\"7\">No fixture report JSON was supplied to the renderer.</td></tr>"
    allowed = "\n".join(f"<li>{html.escape(item)}</li>" for item in summary.get("claims_allowed") or [])
    blocked = "\n".join(f"<li>{html.escape(item)}</li>" for item in summary.get("claims_not_allowed") or [])

    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>ShyftR Phase 11 Benchmark Closeout</title>
<style>
:root {{
  --ink: #10211d;
  --paper: #f3efe3;
  --panel: #fff9e9;
  --rule: #24352f;
  --brass: #c58a2c;
  --oxide: #5e7f74;
  --accent: #e45232;
  --shadow: 0 22px 60px rgba(16, 33, 29, .18);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  color: var(--ink);
  background:
    radial-gradient(circle at 12% 12%, rgba(197,138,44,.22), transparent 26rem),
    radial-gradient(circle at 92% 4%, rgba(94,127,116,.25), transparent 24rem),
    linear-gradient(135deg, #eee5cf 0%, #f8f3e6 50%, #dfd3bb 100%);
  font-family: Georgia, 'Times New Roman', serif;
}}
body::before {{
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: .22;
  background-image: linear-gradient(90deg, rgba(16,33,29,.08) 1px, transparent 1px), linear-gradient(rgba(16,33,29,.06) 1px, transparent 1px);
  background-size: 44px 44px;
}}
main {{ width: min(1180px, calc(100vw - 40px)); margin: 0 auto; padding: 56px 0 80px; }}
.hero {{
  position: relative;
  padding: 46px;
  border: 2px solid var(--rule);
  background: rgba(255,249,233,.9);
  box-shadow: var(--shadow);
  overflow: hidden;
}}
.hero::after {{
  content: 'PHASE 11';
  position: absolute;
  right: -16px;
  bottom: -32px;
  font-size: clamp(64px, 14vw, 180px);
  font-weight: 900;
  line-height: .8;
  color: rgba(197,138,44,.18);
  letter-spacing: -.08em;
}}
.kicker {{ font: 700 13px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .18em; text-transform: uppercase; color: var(--accent); }}
h1 {{ margin: 16px 0 10px; max-width: 860px; font-size: clamp(44px, 7vw, 92px); line-height: .86; letter-spacing: -.055em; }}
.lede {{ max-width: 760px; font-size: 20px; line-height: 1.55; }}
.metrics {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 34px; }}
.metric {{ border: 1px solid var(--rule); background: #f8f0d8; padding: 18px; }}
.metric strong {{ display: block; font: 800 36px/1 ui-monospace, SFMono-Regular, Menlo, monospace; }}
.metric span {{ display: block; margin-top: 8px; font: 700 11px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .11em; text-transform: uppercase; color: var(--oxide); }}
section {{ margin-top: 28px; padding: 30px; border: 1px solid rgba(16,33,29,.65); background: rgba(255,249,233,.76); }}
h2 {{ margin: 0 0 18px; font-size: 34px; letter-spacing: -.03em; }}
.dataset-grid {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; }}
.dataset-card {{ min-height: 220px; padding: 18px; border: 1px solid var(--rule); background: linear-gradient(180deg, #fff8e8, #eee1c9); display: flex; flex-direction: column; }}
.dataset-card h3 {{ margin: 10px 0; font-size: 24px; letter-spacing: -.035em; }}
.dataset-card p {{ flex: 1; line-height: 1.35; }}
.dataset-card span {{ font-size: 13px; color: var(--oxide); }}
.eyebrow {{ font: 800 10px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .12em; text-transform: uppercase; color: var(--accent); }}
table {{ width: 100%; border-collapse: collapse; overflow: hidden; }}
th, td {{ padding: 12px 10px; border-bottom: 1px solid rgba(16,33,29,.25); text-align: left; vertical-align: top; }}
th {{ font: 800 11px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .12em; text-transform: uppercase; color: var(--oxide); }}
.claims {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
.claim-box {{ border: 1px solid var(--rule); padding: 20px; background: #f9efd5; }}
.claim-box.blocked {{ background: #f7dfd2; }}
li {{ margin: 8px 0; line-height: 1.45; }}
.footer {{ margin-top: 20px; font: 12px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; color: rgba(16,33,29,.72); }}
@media (max-width: 900px) {{ .metrics, .dataset-grid, .claims {{ grid-template-columns: 1fr; }} .hero {{ padding: 30px; }} }}
</style>
</head>
<body>
<main>
  <header class=\"hero\">
    <div class=\"kicker\">External memory benchmarking closeout</div>
    <h1>Governed memory, measured without myth.</h1>
    <p class=\"lede\">Phase 11 closes with a reproducible benchmark track: fixture-safe runs, optional comparator adapters, LOCOMO-style local mapping, guarded conversion, run controls, and explicit claim limits.</p>
    <div class=\"metrics\">
      <div class=\"metric\"><strong>{len(summary.get('tranches') or [])}</strong><span>tranches closed</span></div>
      <div class=\"metric\"><strong>{summary.get('report_count', 0)}</strong><span>fixture reports rendered</span></div>
      <div class=\"metric\"><strong>{measured}</strong><span>backend runs ok</span></div>
      <div class=\"metric\"><strong>{skipped}/{failed}</strong><span>skipped / failed</span></div>
    </div>
  </header>

  <section>
    <h2>Benchmark coverage map</h2>
    <div class=\"dataset-grid\">{dataset_cards}</div>
  </section>

  <section>
    <h2>Measured fixture backend results</h2>
    <table><thead><tr><th>Dataset</th><th>Backend</th><th>Status</th><th>Recall</th><th>Precision</th><th>MRR</th><th>Provenance</th></tr></thead><tbody>{backend_table}</tbody></table>
  </section>

  <section>
    <h2>Phase 11 tranche ledger</h2>
    <table><thead><tr><th>Tranche</th><th>Delivered surface</th><th>Status</th></tr></thead><tbody>{tranche_rows}</tbody></table>
  </section>

  <section>
    <h2>Claim discipline</h2>
    <div class=\"claims\">
      <div class=\"claim-box\"><div class=\"eyebrow\">Allowed</div><ul>{allowed}</ul></div>
      <div class=\"claim-box blocked\"><div class=\"eyebrow\">Not allowed</div><ul>{blocked}</ul></div>
    </div>
  </section>

  <p class=\"footer\">Generated at {html.escape(str(summary.get('generated_at')))} from git {html.escape(str(summary.get('git_sha')))}. This HTML is a closeout dossier, not a broad public performance claim.</p>
</main>
</body>
</html>
"""


def generate_phase11_report(*, report_paths: List[Path], output_html: Path, output_json: Path, git_sha: str = "unknown") -> Dict[str, Any]:
    reports = [_load_report(path) for path in report_paths]
    summary = _build_summary(reports, git_sha=git_sha)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_text = "\n".join(line.rstrip() for line in _render_html(summary).splitlines()) + "\n"
    output_html.write_text(html_text, encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the Phase 11 benchmark closeout JSON and polished HTML dossier.")
    parser.add_argument("--report", action="append", default=[], help="Benchmark report JSON path to include. Repeatable.")
    parser.add_argument("--output-html", default="docs/benchmarks/phase11-final-benchmark-report.html")
    parser.add_argument("--output-json", default="docs/benchmarks/phase11-final-benchmark-report.json")
    parser.add_argument("--git-sha", default="unknown")
    args = parser.parse_args()
    generate_phase11_report(
        report_paths=[Path(item) for item in args.report],
        output_html=Path(args.output_html),
        output_json=Path(args.output_json),
        git_sha=str(args.git_sha),
    )
    print(args.output_html)
    print(args.output_json)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
