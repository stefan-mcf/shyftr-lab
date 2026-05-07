"""Compatibility wrapper for the legacy loadout API surface.

The canonical runtime API lives in pack_api.py. This module re-exports it so
existing integrations keep working during Phase 1 stabilization, including
legacy tests and internal imports that reach compatibility helpers directly.
"""
from __future__ import annotations

from .pack_api import (
    RuntimeLoadoutRequest,
    RuntimeLoadoutResponse,
    _categorize_item,
    _detect_risk_flags,
    _item_to_dict,
    process_runtime_loadout_request,
)

__all__ = [
    "RuntimeLoadoutRequest",
    "RuntimeLoadoutResponse",
    "process_runtime_loadout_request",
    "_categorize_item",
    "_detect_risk_flags",
    "_item_to_dict",
]
