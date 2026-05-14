#!/usr/bin/env python3
"""Audit user-facing ShyftR memory vocabulary boundaries."""
from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {'.md','.py','.sh','.json','.yaml','.yml','.toml','.tsx','.ts','.css','.html'}
SKIP_PARTS = {'.git','node_modules','.pytest_cache','__pycache__','.mypy_cache','.ruff_cache','dist','build','.venv','venv'}
SKIP_FILES = {
    'apps/console/package-lock.json',
    # Generated audit output. Excluding it prevents recursive ledger growth when
    # --write-ledger is run repeatedly.
    '.shyftr-demo/memory-vocabulary-modernization-ledger.md',
}
FORBIDDEN_TOKENS = ('charge', 'trace')
FORBIDDEN_FIELDS = (
    'charge_id', 'charge_ids',
    'trace_id', 'trace_ids',
    'source_trace_ids', 'applied_trace_ids', 'useful_trace_ids', 'harmful_trace_ids', 'ignored_trace_ids',
    'selected_charge_ids', 'excluded_charge_ids', 'applied_charge_ids', 'useful_charge_ids', 'harmful_charge_ids', 'ignored_charge_ids',
    'replacement_charge_id',
)

COMPATIBILITY_FILES = {
    'src/shyftr/models.py',
    'src/shyftr/promote.py',
    'src/shyftr/resonance.py',
    'src/shyftr/frontier.py',
    'src/shyftr/federation.py',
    'src/shyftr/cli.py',
    'src/shyftr/provider/memory.py',
    'src/shyftr/mutations.py',
    'src/shyftr/loadout.py',
    'src/shyftr/integrations/loadout_api.py',
    'src/shyftr/integrations/outcome_api.py',
    'src/shyftr/observability.py',
    'scripts/audit_memory_vocabulary.py',
    'scripts/terminology_inventory.py',
}
COMPATIBILITY_DOCS = {
    'docs/concepts/terminology-compatibility.md',
    '.shyftr-demo/memory-vocabulary-modernization-ledger.md',
}
COMPATIBILITY_TEST_PREFIXES = ('tests/',)
ARCHIVAL_PREFIXES = ('local-only-plans/', 'local-only-sources/', 'local-only-feeds/')
ARCHIVAL_ROOT_DOC_PREFIXES = (
    '2026-05-07-shyftr-phase-',
    '2026-05-14-shyftr-phase-',
)
ARCHIVAL_ROOT_DOCS = {
    'broad-roadmap-concept.md',
    'deep-research-report.md',
    'phase-3-pass-off-report.md',
    'phase0-current-state-baseline-implementation-report.md',
    'phase1-implementation-guide.md',
}
PUBLIC_PREFIXES = ('README.md','CONTRIBUTING.md','SECURITY.md','CHANGELOG.md','docs/','examples/','apps/console/src/')

@dataclass(frozen=True)
class Match:
    path: str
    line_no: int
    token: str
    classification: str
    line: str


def tracked_files() -> list[Path]:
    try:
        output = subprocess.check_output(['git','ls-files','--others','--exclude-standard'], cwd=ROOT, text=True)
        files = [ROOT / line for line in output.splitlines() if line]
    except Exception:
        files = []
        for item in ROOT.rglob('*'):
            if item.is_file():
                files.append(item)
    try:
        output = subprocess.check_output(['git','ls-files'], cwd=ROOT, text=True)
        files.extend(ROOT / line for line in output.splitlines() if line)
    except Exception:
        pass
    clean=[]
    seen=set()
    for path in files:
        rel=path.relative_to(ROOT).as_posix()
        if rel in seen or rel in SKIP_FILES:
            continue
        seen.add(rel)
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix in TEXT_SUFFIXES and path.exists():
            clean.append(path)
    return sorted(clean)


def classify(rel: str, line: str) -> str:
    low=line.lower()
    if rel in COMPATIBILITY_DOCS:
        return 'allowed_compatibility_doc'
    if rel in COMPATIBILITY_FILES or rel.startswith('src/shyftr/'):
        return 'allowed_compatibility_reader'
    if rel.startswith(COMPATIBILITY_TEST_PREFIXES):
        return 'allowed_compatibility_test'
    if rel.startswith(ARCHIVAL_PREFIXES):
        return 'allowed_compatibility_doc'
    if rel.startswith(ARCHIVAL_ROOT_DOC_PREFIXES) or rel in ARCHIVAL_ROOT_DOCS:
        return 'allowed_compatibility_doc'
    if 'compatib' in low or 'deprecated' in low or 'migration' in low or 'alias' in low:
        return 'allowed_compatibility_doc'
    if rel.startswith(PUBLIC_PREFIXES) or rel.endswith(('.py','.tsx','.ts','.json','.sh')):
        return 'must_fix_user_facing'
    return 'must_fix_user_facing'


def scan() -> list[Match]:
    matches=[]
    needles = tuple(sorted(set(FORBIDDEN_FIELDS + FORBIDDEN_TOKENS), key=len, reverse=True))
    for path in tracked_files():
        rel=path.relative_to(ROOT).as_posix()
        try:
            lines=path.read_text(encoding='utf-8').splitlines()
        except UnicodeDecodeError:
            continue
        for line_no,line in enumerate(lines,1):
            lower=line.lower()
            for token in needles:
                if token in lower:
                    matches.append(Match(rel,line_no,token,classify(rel,line),line.strip()))
                    break
    return matches


def write_ledger(matches: list[Match], *, max_examples_per_class: int = 50) -> None:
    out=ROOT/'.shyftr-demo/memory-vocabulary-modernization-ledger.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    counts={}
    for m in matches:
        counts[m.classification]=counts.get(m.classification,0)+1
    lines=['# Memory Vocabulary Modernization Ledger','', 'This file is generated by `scripts/audit_memory_vocabulary.py`.', '', '## Counts','']
    for key in sorted(counts):
        lines.append(f'- `{key}`: {counts[key]}')
    lines.extend(['','## Sample matches',''])
    lines.append(f'The ledger stores up to {max_examples_per_class} examples per classification. Run `python scripts/audit_memory_vocabulary.py --report` for the current full user-facing failure list.')
    lines.append('')
    emitted: dict[str, int] = {}
    for m in matches:
        count = emitted.get(m.classification, 0)
        if count >= max_examples_per_class:
            continue
        emitted[m.classification] = count + 1
        snippet=m.line.replace('|','\\|')[:180]
        lines.append(f'- `{m.classification}` `{m.path}:{m.line_no}` `{m.token}` — {snippet}')
    out.write_text('\n'.join(lines)+'\n', encoding='utf-8')


def print_report(matches: list[Match]) -> None:
    counts={}
    for m in matches:
        counts[m.classification]=counts.get(m.classification,0)+1
    print('Memory vocabulary audit')
    for key in sorted(counts):
        print(f'{key}: {counts[key]}')
    failures=[m for m in matches if m.classification == 'must_fix_user_facing']
    if failures:
        print('\nUser-facing matches:')
        for m in failures[:200]:
            print(f'{m.path}:{m.line_no}:{m.token}: {m.line}')
        if len(failures)>200:
            print(f'... {len(failures)-200} more')


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fail-on-user-facing', action='store_true')
    parser.add_argument('--write-ledger', action='store_true')
    parser.add_argument('--report', action='store_true')
    args=parser.parse_args(argv)
    matches=scan()
    if args.write_ledger:
        write_ledger(matches)
    if args.report or not args.write_ledger:
        print_report(matches)
    if args.fail_on_user_facing and any(m.classification == 'must_fix_user_facing' for m in matches):
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
