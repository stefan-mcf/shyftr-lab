from __future__ import annotations

"""Compatibility alias for runtime loadout integration surfaces.

Phase 2 keeps older import paths stable while pack_api remains the canonical
implementation module.
"""

from .pack_api import (
    RuntimeLoadoutRequest,
    RuntimeLoadoutResponse,
    process_runtime_loadout_request,
    _categorize_item,
    _detect_risk_flags,
    _item_to_dict,
)

__all__ = [
    "RuntimeLoadoutRequest",
    "RuntimeLoadoutResponse",
    "process_runtime_loadout_request",
    "_categorize_item",
    "_detect_risk_flags",
    "_item_to_dict",
]
