from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, Iterable, List, Optional

from .models import TRACE_KINDS


@dataclass(frozen=True)
class BoundaryPolicyResult:
    status: str
    reasons: List[str]

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"


class BoundaryPolicyError(ValueError):
    """Raised when a Source fails ShyftR boundary policy."""

    def __init__(self, reasons: Iterable[str]):
        self.reasons = list(reasons)
        super().__init__("Source rejected by boundary policy: " + "; ".join(self.reasons))


@dataclass(frozen=True)
class ProviderMemoryPolicyResult:
    """Regulator decision for direct memory-provider operations."""

    status: str
    reasons: List[str]
    review_required: bool
    trusted_direct_promotion: bool

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"


_POLLUTION_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "secret or credential material",
        re.compile(
            r"(\b(api[_ -]?key|secret|credential|password|private[_ -]?key)\b\s*(?:[:=]|\bis\b)\s*[^\s]+|\btoken\b\s*[:=]\s*[^\s]+|\bsk-[A-Za-z0-9_-]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)",
            re.IGNORECASE,
        ),
    ),
    (
        "transient task or queue status",
        re.compile(
            r"\b(queue item|queue status|worker_summary|pending_manager_pickup|in_progress|awaiting_manager_review|dependency_blocked)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "branch or worktree state",
        re.compile(r"\b(branch|worktree|git status|HEAD|task/[A-Za-z0-9_.-]+|SANDBOX/active)\b", re.IGNORECASE),
    ),
    (
        "artifact path as memory",
        re.compile(
            r"\b(artifact path|worker-artifacts|worker-manager-results|local-runtime/artifacts|/Users/[^\s]+|/tmp/[^\s]+|\.log\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "completion or closeout log",
        re.compile(r"\b(completion log|closeout|completed successfully|saving session|exit code)\b", re.IGNORECASE),
    ),
    (
        "unsupported verification claim",
        re.compile(r"\b(tests passed|verification (is )?complete|verified complete|all checks passed)\b", re.IGNORECASE),
    ),
)


def check_source_boundary(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    *,
    raise_on_reject: bool = False,
) -> BoundaryPolicyResult:
    """Check raw Source evidence before it can enter a Cell ledger."""
    if not isinstance(text, str) or not text.strip():
        reasons = ["source text is required"]
    else:
        reasons = _matching_reasons(text, prefix="text")

    if metadata:
        for key, value in sorted(metadata.items()):
            if value is None:
                continue
            metadata_text = f"{key}: {value}"
            reasons.extend(_matching_reasons(metadata_text, prefix=str(key)))

    if reasons:
        if raise_on_reject:
            raise BoundaryPolicyError(reasons)
        return BoundaryPolicyResult(status="rejected", reasons=reasons)
    return BoundaryPolicyResult(status="accepted", reasons=[])


def check_provider_memory_policy(
    statement: str,
    kind: str,
    metadata: Optional[Dict[str, Any]] = None,
    *,
    raise_on_reject: bool = False,
) -> ProviderMemoryPolicyResult:
    """Regulator gate for direct memory-provider writes.

    UMS-1 allows a narrow trusted direct-promotion path for explicit memory
    provider writes, but only after the normal boundary pollution checks pass
    and the memory kind is part of ShyftR's reviewed Charge taxonomy. The
    returned decision must be recorded with the review event so automatic
    approval remains auditable.
    """
    boundary = check_source_boundary(statement, metadata=metadata)
    reasons = list(boundary.reasons)
    if kind not in TRACE_KINDS:
        reasons.append(f"kind: unsupported memory kind {kind!r}")
    if reasons:
        if raise_on_reject:
            raise BoundaryPolicyError(reasons)
        return ProviderMemoryPolicyResult(
            status="rejected",
            reasons=reasons,
            review_required=True,
            trusted_direct_promotion=False,
        )
    return ProviderMemoryPolicyResult(
        status="accepted",
        reasons=[],
        review_required=False,
        trusted_direct_promotion=True,
    )


def _matching_reasons(text: str, *, prefix: str) -> List[str]:
    matches: List[str] = []
    for reason, pattern in _POLLUTION_RULES:
        if pattern.search(text):
            matches.append(f"{prefix}: {reason}")
    return matches
