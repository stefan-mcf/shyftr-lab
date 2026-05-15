"""Challenger audit loop for ShyftR Cell ledgers.

This package re-exports symbols from the flat ``shyftr.audit`` module so
that ``from shyftr.audit import ...`` resolves them via the package path.

The flat module ``src/shyftr/audit.py`` contains the canonical implementations.
We use importlib to bypass Python's package-shadow-module resolution and
avoid the known-bad circular-import pattern (``from .. import audit as _flat``).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Load the flat shyftr.audit.py module under a synthetic key to bypass the
# package-shadow-module behaviour (shyftr/audit/__init__.py shadows shyftr/audit.py).
_flat_path = Path(__file__).resolve().parent.parent / "audit.py"
_spec = importlib.util.spec_from_file_location("shyftr._audit_flat", _flat_path)
_audit_flat = importlib.util.module_from_spec(_spec)
_sys_modules_key = "shyftr._audit_flat"
sys.modules[_sys_modules_key] = _audit_flat
_spec.loader.exec_module(_audit_flat)  # type: ignore[union-attr]

# ---------------------------------------------------------------------------
# Re-export all public symbols — basic audit row helpers
# ---------------------------------------------------------------------------
append_audit_row = _audit_flat.append_audit_row
build_audit_row = _audit_flat.build_audit_row
read_audit_rows = _audit_flat.read_audit_rows
read_audit_rows_for_target = _audit_flat.read_audit_rows_for_target
read_audit_rows_by_action = _audit_flat.read_audit_rows_by_action

# ---------------------------------------------------------------------------
# Re-export all public symbols — audit spark helpers (challenger)
# ---------------------------------------------------------------------------
CHALLENGER_FINDING_CLASSIFICATIONS = _audit_flat.CHALLENGER_FINDING_CLASSIFICATIONS
build_audit_spark = _audit_flat.build_audit_spark
append_audit_spark = _audit_flat.append_audit_spark
read_audit_sparks = _audit_flat.read_audit_sparks

# ---------------------------------------------------------------------------
# Re-export all public symbols — read-only summary helpers
# ---------------------------------------------------------------------------
audit_summary = _audit_flat.audit_summary

# ---------------------------------------------------------------------------
# Re-export all public symbols — audit review helpers
# ---------------------------------------------------------------------------
AUDIT_REVIEW_RESOLUTIONS = _audit_flat.AUDIT_REVIEW_RESOLUTIONS
AUDIT_REVIEW_ACTIONS = _audit_flat.AUDIT_REVIEW_ACTIONS
build_audit_review = _audit_flat.build_audit_review
append_audit_review = _audit_flat.append_audit_review
read_audit_reviews = _audit_flat.read_audit_reviews
read_audit_reviews_for_audit = _audit_flat.read_audit_reviews_for_audit