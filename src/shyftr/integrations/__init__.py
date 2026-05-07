"""ShyftR runtime integration adapter protocols.

This package defines runtime-agnostic protocol interfaces for external
Source and Outcome adapters. All models are dependency-free (standard
library plus existing ShyftR project dependencies only).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .pack_api import RuntimeLoadoutRequest, RuntimeLoadoutResponse, process_runtime_loadout_request
from .outcome_api import RuntimeOutcomeReport, RuntimeOutcomeResponse, process_runtime_outcome_report
from .proposals import RuntimeProposal, export_runtime_proposals, proposal_from_evidence
from .test_harness import AdapterHarnessResult, AdapterTestHarness


class IntegrationAdapterError(Exception):
    """Base exception for runtime integration adapter failures."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class IntegrationAdapterWarning(UserWarning):
    """Warning category for non-fatal integration adapter conditions."""


__all__ = [
    "IntegrationAdapterError",
    "IntegrationAdapterWarning",
    "RuntimeLoadoutRequest",
    "RuntimeLoadoutResponse",
    "process_runtime_loadout_request",
    "RuntimeOutcomeReport",
    "RuntimeOutcomeResponse",
    "process_runtime_outcome_report",
    "RuntimeProposal",
    "export_runtime_proposals",
    "proposal_from_evidence",
    "AdapterHarnessResult",
    "AdapterTestHarness",
]
