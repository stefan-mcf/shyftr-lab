from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict

from shyftr.benchmarks.adapters.base import AdapterCostLatencyStats
from shyftr.benchmarks.types import BenchmarkConversation, SearchOutput


@dataclass
class NoMemoryBackendAdapter:
    """No-memory baseline adapter.

    This adapter returns no retrieved items and does not persist anything.
    """

    backend_name: str = "no-memory"

    def __post_init__(self) -> None:
        self._run_id = ""
        self._stats = AdapterCostLatencyStats()
        self._details: Dict[str, Any] = {"note": "no-memory baseline returns empty retrieval"}

    def reset_run(self, run_id: str) -> None:
        self._run_id = str(run_id)
        self._stats = AdapterCostLatencyStats()
        self._details = {"note": "no-memory baseline returns empty retrieval"}

    def ingest_conversation(self, conversation: BenchmarkConversation) -> None:  # noqa: ARG002
        # no-op
        return None

    def search(self, *, query_id: str, query: str, top_k: int) -> SearchOutput:  # noqa: ARG002
        started = time.perf_counter()
        output = SearchOutput(backend_name=self.backend_name, run_id=self._run_id, query_id=query_id, items=[], latency_ms=0.0)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        # record some real timing even though retrieval is empty
        self._stats.search_ms.append(elapsed_ms)
        return output

    def export_retrieval_details(self) -> Dict[str, Any]:
        return dict(self._details)

    def export_cost_latency_stats(self) -> Dict[str, Any]:
        return self._stats.to_dict()

    def close(self) -> None:
        return None


__all__ = ["NoMemoryBackendAdapter"]
