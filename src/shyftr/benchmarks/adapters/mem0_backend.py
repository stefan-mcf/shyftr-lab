from __future__ import annotations

import importlib
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from shyftr.benchmarks.adapters.base import AdapterCostLatencyStats, AdapterSkip
from shyftr.benchmarks.types import BenchmarkConversation, RetrievalItem, SearchOutput


def _import_mem0() -> Any:
    """Import mem0 OSS Python package if installed.

    This intentionally does not support mem0 Cloud / API-key flows.
    """

    spec = importlib.util.find_spec("mem0")
    if spec is None:
        raise AdapterSkip(
            "mem0 (OSS) Python package not installed. Install an OSS/local mem0 package to enable this backend. "
            "This harness does not auto-install optional deps."
        )

    mod = importlib.import_module("mem0")
    return mod


def _construct_mem0_memory(mem0_mod: Any) -> Any:
    """Best-effort construction for mem0 OSS memory object.

    mem0 OSS APIs may differ by version; we keep this adapter defensive and avoid
    cloud configuration.
    """

    # Common pattern in mem0 docs: from mem0 import Memory
    Memory = getattr(mem0_mod, "Memory", None)
    if Memory is not None:
        try:
            return Memory()
        except TypeError:
            # Some versions expect config dict.
            return Memory(config={})

    # Some versions may expose a factory.
    factory = getattr(mem0_mod, "create_memory", None)
    if callable(factory):
        return factory({})

    raise AdapterSkip("mem0 import succeeded but no supported OSS Memory API was found (expected mem0.Memory or mem0.create_memory).")


@dataclass
class Mem0OSSBackendAdapter:
    """mem0 OSS/local backend adapter.

    Optional dependency: mem0 Python package. If missing, the adapter raises
    AdapterSkip so the runner can report status=skipped.

    Notes:
    - This adapter is intentionally fixture-safe: it only ingests the synthetic
      fixture payload passed by the harness, and returns RetrievalItem.item_id
      using the fixture message_id values when possible.
    - Cloud / API-key paths are out-of-scope for P11-2.
    """

    backend_name: str = "mem0-oss"

    def __post_init__(self) -> None:
        self._run_id = ""
        self._stats = AdapterCostLatencyStats()
        self._details: Dict[str, Any] = {"backend": "mem0-oss", "mode": "local"}
        self._mem0 = None
        self._memory = None
        self._ingested: List[Dict[str, Any]] = []

    def reset_run(self, run_id: str) -> None:
        self._run_id = str(run_id)
        self._stats = AdapterCostLatencyStats()
        self._details = {"backend": "mem0-oss", "mode": "local"}
        self._ingested = []

        self._mem0 = _import_mem0()
        self._memory = _construct_mem0_memory(self._mem0)

    def ingest_conversation(self, conversation: BenchmarkConversation) -> None:
        if self._memory is None:
            raise RuntimeError("mem0 memory not initialized; did you call reset_run()?")

        started = time.perf_counter()
        # Keep a fixture-safe, stable representation.
        for msg in conversation.messages:
            payload = {
                "id": msg.message_id,
                "conversation_id": conversation.conversation_id,
                "session_id": conversation.session_id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at,
                "metadata": dict(msg.metadata),
            }
            self._ingested.append(payload)

            # Best-effort ingestion into mem0 OSS.
            # We avoid passing any cloud keys/config.
            add_fn = getattr(self._memory, "add", None)
            if callable(add_fn):
                try:
                    add_fn(msg.content, metadata={"message_id": msg.message_id, "conversation_id": conversation.conversation_id})
                except TypeError:
                    # Some versions may expect dict payload.
                    add_fn({"content": msg.content, "metadata": {"message_id": msg.message_id, "conversation_id": conversation.conversation_id}})
            else:
                # If mem0 doesn't have an add API, we can still run in a degraded
                # local mode by relying on adapter-side retrieval details.
                self._details["ingest_warning"] = "mem0 memory object has no .add(); adapter ran in degraded mode."

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        self._stats.ingest_ms = (self._stats.ingest_ms or 0.0) + elapsed_ms

    def search(self, *, query_id: str, query: str, top_k: int) -> SearchOutput:
        if self._memory is None:
            raise RuntimeError("mem0 memory not initialized; did you call reset_run()?")

        started = time.perf_counter()
        items: List[RetrievalItem] = []

        search_fn = getattr(self._memory, "search", None)
        if callable(search_fn):
            raw = None
            try:
                raw = search_fn(query, top_k=top_k)
            except TypeError:
                # Some versions may accept 'k' instead of top_k.
                raw = search_fn(query, k=top_k)

            # Normalize raw results to RetrievalItems.
            # Expected shapes vary, so we accept dicts or objects.
            results = raw or []
            if isinstance(results, dict) and "results" in results:
                results = results.get("results") or []

            for idx, r in enumerate(list(results)[:top_k]):
                if isinstance(r, dict):
                    text = str(r.get("content") or r.get("text") or "")
                    meta = r.get("metadata") or {}
                    item_id = str(meta.get("message_id") or r.get("id") or f"mem0-{query_id}-{idx}")
                    score = r.get("score")
                else:
                    text = str(getattr(r, "content", None) or getattr(r, "text", None) or "")
                    meta = getattr(r, "metadata", None) or {}
                    item_id = str(getattr(r, "id", None) or meta.get("message_id") or f"mem0-{query_id}-{idx}")
                    score = getattr(r, "score", None)

                items.append(
                    RetrievalItem(
                        item_id=item_id,
                        text=text,
                        score=float(score) if score is not None else None,
                        provenance={"backend": self.backend_name, "message_id": meta.get("message_id") or item_id},
                    )
                )
        else:
            # Degraded mode: simple keyword match over ingested fixture for deterministic behavior.
            q = query.lower()
            candidates = []
            for m in self._ingested:
                content = str(m.get("content") or "")
                if any(tok in content.lower() for tok in q.split() if tok):
                    candidates.append(m)
            for idx, m in enumerate(candidates[:top_k]):
                items.append(
                    RetrievalItem(
                        item_id=str(m.get("id") or f"mem0-{query_id}-{idx}"),
                        text=str(m.get("content") or ""),
                        score=None,
                        provenance={"backend": self.backend_name, "message_id": m.get("id")},
                    )
                )
            self._details["search_warning"] = "mem0 memory object has no .search(); adapter ran in degraded keyword mode."

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        self._stats.search_ms.append(elapsed_ms)
        return SearchOutput(backend_name=self.backend_name, run_id=self._run_id, query_id=query_id, items=items, latency_ms=elapsed_ms)

    def export_retrieval_details(self) -> Dict[str, Any]:
        return {
            **dict(self._details),
            "ingested_message_ids": [m.get("id") for m in self._ingested],
        }

    def export_cost_latency_stats(self) -> Dict[str, Any]:
        return self._stats.to_dict()

    def close(self) -> None:
        # Best-effort resource cleanup.
        self._memory = None
        self._mem0 = None


__all__ = ["Mem0OSSBackendAdapter"]
