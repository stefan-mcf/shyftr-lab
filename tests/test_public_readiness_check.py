from __future__ import annotations

from pathlib import Path

from scripts import public_readiness_check as readiness


def test_private_path_pattern_rejects_local_checkout_paths() -> None:
    text = "Run this from /Users/example/ShyftR or /home/example/ShyftR."

    assert any(pattern.search(text) for pattern in readiness.PRIVATE_PATTERNS)


def test_public_files_exclude_local_only_docs() -> None:
    rels = {path.relative_to(readiness.ROOT).as_posix() for path in readiness.public_files()}

    assert not any(rel.startswith("docs/plans/") for rel in rels)
    assert not any(rel.startswith("docs/status/") for rel in rels)
    assert not any(rel.startswith("docs/sources/") for rel in rels)
    assert not any(rel.startswith("docs/runbooks/") for rel in rels)
    assert not any(rel.startswith("docs/feeds/") for rel in rels)
    assert not any(rel.startswith("docs/operations/") for rel in rels)


def test_regex_source_line_allowlist_is_narrow() -> None:
    assert readiness.allowed_private_pattern_match(
        "scripts/public_readiness_check.py",
        '    re.compile(r"/(Users|home)/[^\\s]+"),',
    )
    assert not readiness.allowed_private_pattern_match(
        "local-only-plans/example.md",
        "Run from /Users/example/ShyftR.",
    )
