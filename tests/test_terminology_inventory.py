from __future__ import annotations

from pathlib import Path

from scripts import terminology_inventory as inv


def test_traceback_does_not_create_unclassified_trace_match(tmp_path):
    allowed, reason = inv.is_allowed_stale("docs/demo.md", "Python traceback output")
    assert allowed
    assert reason == "generic traceback"


def test_source_code_is_generic_source_usage():
    allowed, reason = inv.is_allowed_stale("docs/development.md", "Edit the source code locally.")
    assert allowed
    assert reason == "generic source usage"


def test_heading_allows_title_case_lifecycle_terms():
    allowed, reason = inv.is_allowed_capitalized("docs/concepts/plain-language-vocabulary.md", "## Evidence", "Evidence")
    assert allowed
    assert "capitalization" in reason or "heading" in reason


def test_prose_flags_capitalized_canonical_terms():
    allowed, reason = inv.is_allowed_capitalized("README.md", "A Candidate becomes Memory after review.", "Candidate")
    assert not allowed
    assert reason == "capitalized canonical term in prose"


def test_sentence_start_capitalized_term_is_allowed():
    allowed, reason = inv.is_allowed_capitalized("README.md", "Candidate review is explicit.", "Candidate")
    assert allowed
    assert reason == "sentence-start false positive"


def test_migration_docs_allow_legacy_terms():
    allowed, reason = inv.is_allowed_stale("docs/concepts/terminology-compatibility.md", "Pulse maps to Evidence.")
    assert allowed
    assert reason == "migration document"
