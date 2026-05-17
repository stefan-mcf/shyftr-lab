from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


def _fixture_message_id(statement: str, fallback: str) -> str:
    """Extract fixture message id from the synthetic statement prefix."""
    if statement.startswith("[") and "]" in statement:
        prefix = statement.split("]", 1)[0].strip("[]")
        parts = prefix.split("/")
        if len(parts) >= 4 and parts[3]:
            return parts[3]
    return fallback

from shyftr.benchmarks.adapters.base import AdapterCostLatencyStats
from shyftr.benchmarks.types import BenchmarkConversation, RetrievalItem, SearchOutput
from shyftr.layout import init_cell
from shyftr.provider import MemoryProvider


@dataclass
class ShyftRBackendAdapter:
    """ShyftR local-cell backend adapter (Phase 11 harness).

    Notes:
    - This adapter is for fixture-safe, local benchmarking only.
    - It uses MemoryProvider remember_trusted to ingest statements that are
      explicitly public-safe.
    """

    cell_root: Path
    cell_id: str = "bench-cell"
    backend_name: str = "shyftr"
    trust_actor: str = "benchmark-runner"
    trust_reason: str = "synthetic-fixture"
    pulse_channel: str = "benchmark"

    def __post_init__(self) -> None:
        self.cell_root = Path(self.cell_root)
        self._run_id = ""
        self._cell_path: Optional[Path] = None
        self._provider: Optional[MemoryProvider] = None
        self._stats = AdapterCostLatencyStats()
        self._details: Dict[str, Any] = {"searches": []}

    def reset_run(self, run_id: str) -> None:
        self._run_id = str(run_id)
        # Create/ensure cell exists. Bench harness owns where this is rooted
        # (typically a temp directory).
        self._cell_path = init_cell(self.cell_root, self.cell_id, cell_type="benchmark")
        self._provider = MemoryProvider(self._cell_path)
        self._stats = AdapterCostLatencyStats()
        self._details = {"searches": []}

    def ingest_conversation(self, conversation: BenchmarkConversation) -> None:
        if self._provider is None:
            raise RuntimeError("adapter not initialized; call reset_run first")

        started = time.perf_counter()
        # Ingest each message as trusted memory.
        for msg in conversation.messages:
            statement = f"[{conversation.conversation_id}/{conversation.session_id or 'na'}/{msg.role}/{msg.message_id}] {msg.content}"
            # Use 'preference' as it is in TRUSTED_MEMORY_KINDS; content is synthetic.
            self._provider.remember_trusted(
                statement=statement,
                kind="preference",
                actor=self.trust_actor,
                trust_reason=self.trust_reason,
                pulse_channel=self.pulse_channel,
                created_at=msg.created_at or conversation.started_at or "2026-01-01T00:00:00Z",
                metadata={
                    "conversation_id": conversation.conversation_id,
                    "session_id": conversation.session_id,
                    "message_id": msg.message_id,
                    "role": msg.role,
                    "benchmark": True,
                },
            )

        self._stats = AdapterCostLatencyStats(
            ingest_ms=(time.perf_counter() - started) * 1000.0,
            search_ms=list(self._stats.search_ms),
            notes=dict(self._stats.notes),
        )

    def search(self, *, query_id: str, query: str, top_k: int) -> SearchOutput:
        if self._provider is None:
            raise RuntimeError("adapter not initialized; call reset_run first")

        started = time.perf_counter()
        results = self._provider.search(query=query, top_k=int(top_k))
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        self._stats.search_ms.append(elapsed_ms)

        items: List[RetrievalItem] = []
        detail_items: List[Dict[str, Any]] = []
        for r in results:
            item_id = _fixture_message_id(r.statement, r.memory_id)
            item = RetrievalItem(
                item_id=item_id,
                text=r.statement,
                score=float(r.score) if r.score is not None else None,
                provenance={"memory_id": r.memory_id, **dict(r.provenance or {})},
                sensitivity=None,
                review_status=str(r.lifecycle_status or ""),
            )
            items.append(item)
            detail_items.append(
                {
                    "item_id": item.item_id,
                    "score": item.score,
                    "review_status": item.review_status,
                    "has_provenance": bool(item.provenance),
                }
            )

        self._details["searches"].append(
            {
                "query_id": query_id,
                "query": query,
                "top_k": int(top_k),
                "returned": len(items),
                "latency_ms": elapsed_ms,
                "items": detail_items,
            }
        )

        return SearchOutput(
            backend_name=self.backend_name,
            run_id=self._run_id,
            query_id=query_id,
            items=items,
            latency_ms=elapsed_ms,
        )

    def export_retrieval_details(self) -> Dict[str, Any]:
        return dict(self._details)

    def export_cost_latency_stats(self) -> Dict[str, Any]:
        return self._stats.to_dict()

    def close(self) -> None:
        self._provider = None


__all__ = ["ShyftRBackendAdapter"]
