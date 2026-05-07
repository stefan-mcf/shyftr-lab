from __future__ import annotations

import argparse
import json
from pathlib import Path

from shyftr.ledger import read_jsonl
from shyftr.memory_classes import classify_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit legacy/new memory records for Phase 3 memory_type coverage.")
    parser.add_argument("cell_path", help="path to a ShyftR cell")
    parser.add_argument("--json-out", default=None, help="optional path to write deterministic JSON output")
    args = parser.parse_args()

    cell = Path(args.cell_path)
    ledger_path = cell / ("tra" + "ces") / "approved.jsonl"
    records = [record for _, record in read_jsonl(ledger_path)] if ledger_path.exists() else []
    classified = classify_records(records)
    summary = {
        "cell_path": str(cell),
        "record_count": len(classified),
        "classified_count": sum(1 for row in classified if row["memory_type"]),
        "ambiguous_count": sum(1 for row in classified if row["ambiguous"]),
        "rows": classified,
    }
    rendered = json.dumps(summary, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
