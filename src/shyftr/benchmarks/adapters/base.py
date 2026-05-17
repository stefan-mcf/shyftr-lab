from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from shyftr.benchmarks.types import BenchmarkConversation, SearchOutput


@dataclass(frozen=True)
class AdapterCostLatencyStats:
    ingest_ms: Optional[float] = None
    search_ms: List[float] = field(default_factory=list)
    notes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ingest_ms": self.ingest_ms,
            "search_ms": list(self.search_ms),
            "notes": dict(self.notes),
        }


class BackendAdapter(Protocol):
    """Neutral adapter interface for memory backends used by benchmarks."""

    backend_name: str

    def reset_run(self, run_id: str) -> None:
        ...

    def ingest_conversation(self, conversation: BenchmarkConversation) -> None:
        ...

    def search(self, *, query_id: str, query: str, top_k: int) -> SearchOutput:
        ...

    def export_retrieval_details(self) -> Dict[str, Any]:
        ...

    def export_cost_latency_stats(self) -> Dict[str, Any]:
        ...

    def close(self) -> None:
        ...


__all__ = ["BackendAdapter", "AdapterCostLatencyStats"]
