from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
from uuid import uuid4

from shyftr.ledger import append_jsonl
from shyftr.models import Fragment, Source
from shyftr.policy import check_provider_memory_policy
from shyftr.provider.memory import RememberResult, SearchResult, _excerpt, _read_cell_id, _require_text, remember, search

PathLike = Union[str, Path]

TRUSTED_MEMORY_KINDS = frozenset({"preference", "constraint", "workflow", "tool_quirk", "escalation_rule"})
_REQUIRED_METADATA_FIELDS = ("actor", "trust_reason", "pulse_channel", "created_at")


@dataclass(frozen=True)
class TrustedRememberResult:
    charge_id: Optional[str]
    pulse_id: str
    spark_id: str
    status: str
    trust_tier: str = "trace"
    trusted_direct_promotion: bool = True
    memory_type: Optional[str] = None


class TrustedMemoryProvider:
    """Explicit trusted-memory facade for one Cell.

    The trusted path is intentionally narrow: callers must identify who made
    the trusted assertion, why it is trusted, where the Pulse came from, and
    when it was created. Trusted direct promotion still goes through the normal
    Source -> Fragment -> review -> promotion -> Trace ledger path and the
    provider Regulator policy.
    """

    def __init__(self, cell_path: PathLike, *, actor: str, pulse_channel: str):
        self.cell_path = Path(cell_path)
        self.actor = _require_metadata_text(actor, "actor")
        self.pulse_channel = _require_metadata_text(pulse_channel, "pulse_channel")

    def remember_trusted(
        self,
        statement: str,
        kind: str,
        *,
        trust_reason: str,
        created_at: Optional[str] = None,
        trusted_direct_promotion: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TrustedRememberResult:
        return remember_trusted(
            self.cell_path,
            statement,
            kind,
            actor=self.actor,
            trust_reason=trust_reason,
            pulse_channel=self.pulse_channel,
            created_at=created_at or _now(),
            trusted_direct_promotion=trusted_direct_promotion,
            metadata=metadata,
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
        trust_tiers: Optional[Sequence[str]] = None,
        kinds: Optional[Sequence[str]] = None,
    ) -> List[SearchResult]:
        return search(self.cell_path, query, top_k=top_k, trust_tiers=trust_tiers, kinds=kinds)


def remember_trusted(
    cell_path: PathLike,
    statement: str,
    kind: str,
    *,
    actor: str,
    trust_reason: str,
    pulse_channel: str,
    created_at: str,
    trusted_direct_promotion: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> TrustedRememberResult:
    """Store explicit trusted memory with required provenance metadata.

    Direct promotion can be disabled per call. In that mode ShyftR still
    captures the Source/Pulse and Fragment/Spark evidence for review, but it
    does not create an approved Charge/Trace automatically.
    """
    clean_statement = _require_text(statement, "statement")
    clean_kind = _require_metadata_text(kind, "kind")
    _validate_trusted_kind(clean_kind)
    trusted_metadata = _trusted_metadata(
        metadata,
        actor=actor,
        trust_reason=trust_reason,
        pulse_channel=pulse_channel,
        created_at=created_at,
        trusted_direct_promotion=trusted_direct_promotion,
    )
    check_provider_memory_policy(clean_statement, clean_kind, metadata=trusted_metadata, raise_on_reject=True)

    if trusted_direct_promotion:
        result: RememberResult = remember(
            cell_path,
            clean_statement,
            clean_kind,
            pulse_context={"channel": trusted_metadata["pulse_channel"], "actor": trusted_metadata["actor"]},
            metadata=trusted_metadata,
        )
        return TrustedRememberResult(
            charge_id=result.charge_id,
            pulse_id=result.pulse_id,
            spark_id=result.spark_id,
            status=result.status,
            trust_tier=result.trust_tier,
            trusted_direct_promotion=True,
            memory_type=result.memory_type,
        )

    pulse_id, spark_id = _append_pending_trusted_evidence(
        cell_path,
        clean_statement,
        clean_kind,
        metadata=trusted_metadata,
    )
    return TrustedRememberResult(
        charge_id=None,
        pulse_id=pulse_id,
        spark_id=spark_id,
        status="pending_review",
        trusted_direct_promotion=False,
    )


def _trusted_metadata(
    metadata: Optional[Dict[str, Any]],
    *,
    actor: str,
    trust_reason: str,
    pulse_channel: str,
    created_at: str,
    trusted_direct_promotion: bool,
) -> Dict[str, Any]:
    combined = dict(metadata or {})
    combined.update(
        {
            "actor": _require_metadata_text(actor, "actor"),
            "trust_reason": _require_metadata_text(trust_reason, "trust_reason"),
            "pulse_channel": _require_metadata_text(pulse_channel, "pulse_channel"),
            "created_at": _require_metadata_text(created_at, "created_at"),
            "provider_api": "remember_trusted",
            "trusted_direct_promotion": bool(trusted_direct_promotion),
        }
    )
    for field in _REQUIRED_METADATA_FIELDS:
        _require_metadata_text(combined.get(field), field)
    return combined


def _require_metadata_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required for trusted memory")
    return value.strip()


def _validate_trusted_kind(kind: str) -> None:
    if kind not in TRUSTED_MEMORY_KINDS:
        raise ValueError(f"unsupported trusted memory kind: {kind}")


def _append_pending_trusted_evidence(
    cell_path: PathLike,
    statement: str,
    kind: str,
    *,
    metadata: Dict[str, Any],
) -> tuple[str, str]:
    cell = Path(cell_path)
    cell_id = _read_cell_id(cell)
    digest = hashlib.sha256(statement.encode("utf-8")).hexdigest()
    now = _now()
    source = Source(
        source_id=f"src-{uuid4().hex}",
        cell_id=cell_id,
        kind=kind,
        sha256=digest,
        captured_at=now,
        uri=None,
        metadata=metadata,
    )
    append_jsonl(cell / "ledger" / "sources.jsonl", source.to_dict())

    fragment = Fragment(
        fragment_id=f"frag-{uuid4().hex}",
        source_id=source.source_id,
        cell_id=cell_id,
        kind=kind,
        text=statement,
        source_excerpt=_excerpt(statement),
        boundary_status="accepted",
        review_status="pending",
        confidence=0.8,
        tags=list(metadata.get("tags", [])) if isinstance(metadata.get("tags"), list) else [],
    )
    append_jsonl(cell / "ledger" / "fragments.jsonl", fragment.to_dict())
    return source.source_id, fragment.fragment_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
