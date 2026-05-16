#!/usr/bin/env python3
"""Inventory ShyftR terminology during the plain-language rename."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = [
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "docs",
    "examples",
    "src/shyftr",
    "tests",
    "apps/console/src",
    "scripts",
]
TEXT_SUFFIXES = {".md", ".py", ".sh", ".json", ".yaml", ".yml", ".toml", ".tsx", ".ts", ".css", ".html"}

STALE_TERMS = {
    "power_theme": ["pulse", "spark", "charge", "coil", "rail"],
    "legacy_implementation": ["source", "fragment", "trace", "alloy", "doctrine"],
    "support_legacy": ["loadout", "outcome", "signal", "isolation", "feed", "boundary", "circuit"],
}
CANONICAL_CAPITALIZED = ["Evidence", "Candidate", "Memory", "Pattern", "Rule", "Cell", "Regulator", "Grid", "Pack", "Feedback", "Quarantine"]

MIGRATION_DOCS = {
    "docs/concepts/terminology-compatibility.md",
    "local-only-sources/2026-05-06-shyftr-plain-lifecycle-naming-review.md",
}
COMPATIBILITY_FILES = {
    "src/shyftr/models.py",
    "src/shyftr/layout.py",
    "src/shyftr/cli.py",
    "src/shyftr/integrations/loadout_api.py",
    "src/shyftr/integrations/outcome_api.py",
    "src/shyftr/distill/alloys.py",
    "src/shyftr/distill/doctrine.py",
    "scripts/audit_memory_vocabulary.py",
    "scripts/terminology_inventory.py",
}
HISTORICAL_PREFIXES = ("local-only-sources/", "local-only-feeds/")
PUBLIC_CURRENT_PREFIXES = ("docs/concepts/", "docs/demo", "docs/api.md", "docs/console.md", "examples/")
BASELINE_COMPATIBILITY_PREFIXES = (
    "examples/evals/current-state-baseline/",
    "scripts/current_state_baseline.py",
    "scripts/compare_current_state_baseline.py",
)

@dataclass(frozen=True)
class Match:
    path: str
    line_no: int
    term: str
    category: str
    line: str
    allowed: bool
    reason: str


def iter_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    files: list[Path] = []
    for rel in proc.stdout.splitlines():
        if not rel:
            continue
        if not (rel in SCAN_ROOTS or any(rel.startswith(f"{root}/") for root in SCAN_ROOTS if root != rel)):
            continue
        path = ROOT / rel
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            files.append(path)
    return sorted(set(files))


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_allowed_stale(rel: str, line: str) -> tuple[bool, str]:
    low = line.lower()
    if rel in MIGRATION_DOCS:
        return True, "migration document"
    if rel in COMPATIBILITY_FILES:
        return True, "compatibility implementation/test"
    if rel.startswith(("src/shyftr/", "tests/", "apps/console/src/")):
        return True, "implementation or test compatibility surface"
    if rel.startswith(HISTORICAL_PREFIXES):
        return True, "historical source/feed archive"
    if rel.startswith(BASELINE_COMPATIBILITY_PREFIXES):
        return True, "baseline compatibility harness"
    if rel.startswith("local-only-plans/") and "2026-05-06-shyftr-plain-language" not in rel:
        return True, "historical/archival plan"
    if "legacy" in low or "compatib" in low or "deprecated" in low or "alias" in low or "old " in low:
        return True, "explicit compatibility/historical context"
    if "traceback" in low:
        return True, "generic traceback"
    if "source of truth" in low or "source truth" in low:
        return True, "generic authority-source usage"
    if "historical" in low or "implementation notes" in low or "future-planning" in low:
        return True, "historical/document classification context"
    if "local data boundary" in low or "trust boundary" in low or "trust-boundary" in low or "alpha status boundary" in low or "non-hosted/non-production boundary" in low or "regulator boundary" in low or "safety boundary" in low or "product boundary" in low or "scope boundary" in low or "authority boundary" in low or "cleanup boundary" in low or "alpha boundary" in low or "future-capability boundary" in low or "current boundary" in low or "rule boundary" in low:
        return True, "generic safety boundary usage"
    if "source_cell" in low or "source cell" in low or "federation source" in low:
        return True, "provenance source-cell field"
    if "source .venv/bin/activate" in low or ". .venv/bin/activate" in low:
        return True, "shell activation command"
    if "source code" in low or "open source" in low or "source file" in low or "source material" in low or "source note" in low or "source identity" in low or "source metadata" in low or "source hash" in low or "source id" in low or "source reference" in low or "source category" in low or "source module" in low or "source workspace" in low or "source context" in low or "source memory" in low or "source tree" in low or "source-tree" in low or "source-root" in low or "source_root" in low or "providing the sources" in low or "source and target" in low or "source quality" in low or "source ledger" in low or "source evidence" in low or "proposal source" in low or "truth source" in low or "the source." in low or "report_feed" in low or "source summary schema" in low:
        return True, "generic source usage"
    if "runtimeoutcomereport" in low:
        return True, "compatibility API class name"
    if "operation=\"signal\"" in low or "signal_latency_ms" in low or "signal latency" in low or "hygiene and safety signals" in low or "hygiene_and_safety_signals" in low:
        return True, "structured metric/safety signal usage"
    return False, "unclassified"


def is_heading_or_table(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("#") or stripped.startswith("|") or stripped.startswith("-") and stripped.endswith(":")


def is_code_or_link_context(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("```") or "`" in stripped or ".py" in stripped or "http" in stripped


def is_allowed_capitalized(rel: str, line: str, term: str) -> tuple[bool, str]:
    stripped = line.strip()
    if rel.endswith(".py") or rel.endswith(".ts") or rel.endswith(".tsx") or rel.endswith(".json"):
        return True, "code or structured file"
    if rel in MIGRATION_DOCS or rel == "docs/concepts/plain-language-vocabulary.md":
        return True, "migration/glossary capitalization context"
    if rel.startswith(("local-only-plans/", "local-only-sources/", "local-only-feeds/", "tests/")):
        return True, "historical or test capitalization context"
    if is_heading_or_table(line) or is_code_or_link_context(line):
        return True, "heading/table/code context"
    prefix = stripped[: len(term)]
    if prefix == term:
        return True, "sentence-start false positive"
    if term == "ShyftR":
        return True, "product name"
    return False, "capitalized canonical term in prose"


def scan() -> list[Match]:
    matches: list[Match] = []
    term_patterns: list[tuple[str, str, re.Pattern[str]]] = []
    for category, terms in STALE_TERMS.items():
        for term in terms:
            term_patterns.append((category, term, re.compile(rf"\b{re.escape(term)}s?\b", re.IGNORECASE)))
    cap_patterns = [("capitalized_prose", term, re.compile(rf"\b{re.escape(term)}\b")) for term in CANONICAL_CAPITALIZED]

    for path in iter_files():
        rel = relpath(path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(lines, 1):
            for category, term, pattern in term_patterns:
                if not pattern.search(line):
                    continue
                allowed, reason = is_allowed_stale(rel, line)
                matches.append(Match(rel, line_no, term, category, line.strip(), allowed, reason))
            for category, term, pattern in cap_patterns:
                if not pattern.search(line):
                    continue
                allowed, reason = is_allowed_capitalized(rel, line, term)
                matches.append(Match(rel, line_no, term, category, line.strip(), allowed, reason))
    return matches


def print_report(matches: list[Match]) -> None:
    totals: dict[str, int] = {}
    unclassified: list[Match] = []
    for m in matches:
        key = f"{m.category}:{'allowed' if m.allowed else 'unclassified'}"
        totals[key] = totals.get(key, 0) + 1
        if not m.allowed:
            unclassified.append(m)
    print("Terminology inventory")
    for key in sorted(totals):
        print(f"{key}: {totals[key]}")
    if unclassified:
        print("\nUnclassified matches:")
        for m in unclassified[:300]:
            print(f"{m.path}:{m.line_no}: {m.category}:{m.term}: {m.line}")
        if len(unclassified) > 300:
            print(f"... {len(unclassified) - 300} more")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--fail-on-public-stale", action="store_true")
    parser.add_argument("--fail-on-capitalized-prose", action="store_true")
    args = parser.parse_args(argv)
    if not (args.report or args.fail_on_public_stale or args.fail_on_capitalized_prose):
        args.report = True
    matches = scan()
    if args.report:
        print_report(matches)
    failures: list[Match] = []
    if args.fail_on_public_stale:
        failures.extend(m for m in matches if not m.allowed and m.category != "capitalized_prose")
    if args.fail_on_capitalized_prose:
        failures.extend(m for m in matches if not m.allowed and m.category == "capitalized_prose")
    if failures:
        if not args.report:
            print_report(failures)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
