"""Compatibility shim for the legacy loadout surface.

Pack is the canonical implementation surface. This module re-exports the pack
implementation so existing imports keep working during Phase 1 stabilization.
"""
from __future__ import annotations

from .pack import (
    AssembledLoadout,
    AssembledPack,
    LOADOUT_ROLES,
    LoadoutItem,
    LoadoutTaskInput,
    PackItem,
    PackTaskInput,
    RetrievalLog,
    _build_candidate_from_fragment,
    _build_candidate_from_trace,
    assemble_loadout,
    assemble_pack,
    estimate_tokens,
    is_operational_state,
)

__all__ = [
    "AssembledLoadout",
    "AssembledPack",
    "LOADOUT_ROLES",
    "LoadoutItem",
    "LoadoutTaskInput",
    "PackItem",
    "PackTaskInput",
    "RetrievalLog",
    "_build_candidate_from_fragment",
    "_build_candidate_from_trace",
    "assemble_loadout",
    "assemble_pack",
    "estimate_tokens",
    "is_operational_state",
]
