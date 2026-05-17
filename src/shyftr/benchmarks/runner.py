from __future__ import annotations

import math
import os
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from shyftr.benchmarks.adapters.base import AdapterSkip, BackendAdapter
from shyftr.benchmarks.fixture import BenchmarkFixture
from shyftr.benchmarks.report import BackendResult, BenchmarkReport, REPORT_SCHEMA_VERSION, utc_now_iso
from shyftr.benchmarks.types import RetrievalItem, SearchOutput


@dataclass(frozen=True)
class HarnessFairnessConfig:
    top_k_values: List[int]
    timeout_seconds: int = 60
    max_retries: int = 0
    cold_run: bool = True
    answerer_owned_by_runner: bool = True
    judge_owned_by_runner: bool = True
    backend_answering_enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "top_k_values": list(self.top_k_values),
            "timeout_seconds": int(self.timeout_seconds),
            "max_retries": int(self.max_retries),
            "cold_run": bool(self.cold_run),
            "answerer_owned_by_runner": bool(self.answerer_owned_by_runner),
            "judge_owned_by_runner": bool(self.judge_owned_by_runner),
            "backend_answering_enabled": bool(self.backend_answering_enabled),
        }


def _safe_write_path(output_path: Path, *, repo_root: Path) -> Path:
    """Restrict report output to safe locations.

    Allowed:
    - <repo_root>/artifacts/...
    - <repo_root>/reports/...
    - <repo_root>/tmp/...

    This prevents accidental writes outside the repo during local harness runs.
    """

    output_path = output_path.expanduser().resolve()
    repo_root = repo_root.expanduser().resolve()

    allowed_roots = [repo_root / "artifacts", repo_root / "reports", repo_root / "tmp"]
    if any(_is_relative_to(output_path, root) for root in allowed_roots):
        return output_path
    raise ValueError(f"Refusing to write report outside allowed roots: {output_path}")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _token_estimate(text: str) -> int:
    # Keep deterministic and dependency-free.
    return max(1, math.ceil(len(text) / 4))


def _compute_retrieval_metrics(search_outputs: Sequence[SearchOutput], expected_item_ids: Dict[str, List[str]], *, k: int) -> Dict[str, Any]:
    # Simple, fixture-safe retrieval metrics for Phase 11.
    # - relevance is binary by expected_item_ids match on item_id
    # - If expected_item_ids missing, skip metrics for that question.

    total_questions = 0
    recall_sum = 0.0
    precision_sum = 0.0
    mrr_sum = 0.0

    for out in search_outputs:
        expected = expected_item_ids.get(out.query_id)
        if not expected:
            continue
        total_questions += 1
        returned_ids = [i.item_id for i in out.items[:k]]
        relevant_returned = [rid for rid in returned_ids if rid in expected]
        recall = len(set(relevant_returned)) / float(len(set(expected))) if expected else 0.0
        precision = len(set(relevant_returned)) / float(len(set(returned_ids))) if returned_ids else 0.0

        rr = 0.0
        for rank, rid in enumerate(returned_ids, start=1):
            if rid in expected:
                rr = 1.0 / float(rank)
                break

        recall_sum += recall
        precision_sum += precision
        mrr_sum += rr

    if total_questions == 0:
        return {
            "question_count": 0,
            "recall_at_k": None,
            "precision_at_k": None,
            "mrr": None,
        }

    return {
        "question_count": total_questions,
        "recall_at_k": recall_sum / total_questions,
        "precision_at_k": precision_sum / total_questions,
        "mrr": mrr_sum / total_questions,
    }


def _normalize_top_k_values(top_k_values: Sequence[int]) -> List[int]:
    """Return positive, de-duplicated k values while preserving caller order."""

    normalized: List[int] = []
    for raw in top_k_values:
        k = int(raw)
        if k < 1:
            raise ValueError(f"top-k values must be positive integers; got {raw!r}")
        if k not in normalized:
            normalized.append(k)
    return normalized or [10]


def _metrics_by_k(search_outputs: Sequence[SearchOutput], expected_item_ids: Dict[str, List[str]], *, top_k_values: Sequence[int]) -> Dict[str, Dict[str, Any]]:
    return {str(k): _compute_retrieval_metrics(search_outputs, expected_item_ids, k=int(k)) for k in top_k_values}


def _summarize_cost_latency(cost_latency: Dict[str, Any], *, backend_wall_ms: float) -> Dict[str, Any]:
    search_ms = [float(v) for v in cost_latency.get("search_ms", []) if v is not None]
    return {
        "ingest_ms": cost_latency.get("ingest_ms"),
        "search_count": len(search_ms),
        "search_ms_total": sum(search_ms) if search_ms else 0.0,
        "search_ms_avg": (sum(search_ms) / float(len(search_ms))) if search_ms else None,
        "search_ms_max": max(search_ms) if search_ms else None,
        "backend_wall_ms": float(backend_wall_ms),
        "notes": dict(cost_latency.get("notes", {})),
    }


def _aggregate_backend_summaries(backend_results: Sequence[BackendResult], *, timeout_seconds: int) -> Dict[str, Any]:
    status_counts: Dict[str, int] = {}
    cost_latency_by_backend: Dict[str, Any] = {}
    timeout_failures: List[str] = []

    for result in backend_results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
        cost_latency_by_backend[result.backend_name] = result.cost_latency.get("summary", {}) if result.cost_latency else {}
        reason = result.status_reason or ""
        if "timeout" in reason.lower() or "timed out" in reason.lower() or "TimeoutError" in reason:
            timeout_failures.append(result.backend_name)

    return {
        "backends": [r.backend_name for r in backend_results],
        "backend_status_counts": status_counts,
        "cost_latency_summary": cost_latency_by_backend,
        "timeout_summary": {
            "timeout_seconds": int(timeout_seconds),
            "timeout_failures": timeout_failures,
            "timeout_enforcement": "reported_only",
        },
        "note": "Aggregate metrics remain fixture-level and claim-limited in Phase 11.",
    }


def _compute_control_audit(items: Iterable[RetrievalItem]) -> Dict[str, Any]:
    items_list = list(items)
    if not items_list:
        return {
            "provenance_coverage": 0.0,
            "review_gate_compliance": "not_supported",
            "replay_status": "not_run",
            "sensitivity_leak_rate": 0.0,
            "append_only_preservation": "not_run",
            "feedback_visibility": "not_supported",
            "pack_compactness": None,
        }

    with_prov = 0
    unsafe = 0
    total_tokens = 0
    for item in items_list:
        if item.provenance:
            with_prov += 1
        if item.sensitivity and item.sensitivity.lower() in {"private", "secret"}:
            unsafe += 1
        total_tokens += _token_estimate(item.text)

    return {
        "provenance_coverage": with_prov / float(len(items_list)),
        "review_gate_compliance": "not_evaluated",
        "replay_status": "not_run",
        "sensitivity_leak_rate": unsafe / float(len(items_list)),
        "append_only_preservation": "not_run",
        "feedback_visibility": "not_supported",
        "pack_compactness": None if total_tokens == 0 else 1.0,
    }


def run_fixture_benchmark(
    *,
    fixture: BenchmarkFixture,
    adapters: Sequence[BackendAdapter],
    run_id: str,
    output_path: Path,
    repo_root: Path,
    top_k_values: Sequence[int] = (10,),
    include_retrieval_details: bool = True,
    runner_name: str = "run_memory_benchmark.py",
    runner_version: str = "phase11-p11-4a",
    command_argv: Optional[List[str]] = None,
) -> BenchmarkReport:
    normalized_top_k_values = _normalize_top_k_values(top_k_values)
    max_top_k = max(normalized_top_k_values)
    fairness = HarnessFairnessConfig(top_k_values=list(normalized_top_k_values)).to_dict()

    # Runner metadata must be public-safe.
    runner = {
        "name": runner_name,
        "version": runner_version,
        "git_sha": _git_sha_or_unknown(repo_root),
        "command": list(command_argv) if command_argv else None,
        "cwd": str(Path.cwd()),
        "python_version": sys.version.split()[0],
        "environment_notes": {
            "platform": platform.platform(),
            "optional_deps": {},
        },
    }

    dataset = {
        "name": fixture.dataset_name,
        "version": fixture.dataset_version,
        "split": fixture.fixture_id,
        "conversation_count": len(fixture.conversations),
        "question_count": len(fixture.questions),
        "fixture_path": None,
        "contains_private_data": bool(fixture.contains_private_data),
    }

    models = {
        "answerer": {"name": "runner-owned", "version": None},
        "judge": {"name": "runner-owned", "version": None},
        "embedding": {"name": "backend-owned", "version": None},
    }

    report = BenchmarkReport(
        schema_version=REPORT_SCHEMA_VERSION,
        run_id=run_id,
        generated_at=utc_now_iso(),
        runner=runner,
        dataset=dataset,
        fairness=fairness,
        models=models,
        limitations=[
            "Phase 11 fixtures are tiny and public-safe; not a full LOCOMO/LongMemEval/BEAM run.",
            "Answerer/judge are disabled in Phase 11; only retrieval and adapter-status contracts are exercised.",
            "No broad performance or task-success claims are supported by these fixture runs.",
        ],
        claims_allowed=[
            "This report records a fixture-safe retrieval run under a pinned harness configuration.",
        ],
        claims_not_allowed=[
            "No broad performance or superiority claims are supported by this fixture-level run.",
            "No hosted or production claims are supported.",
        ],
    )

    expected_map: Dict[str, List[str]] = {}
    for q in fixture.questions:
        if q.expected_item_ids:
            expected_map[q.question_id] = list(q.expected_item_ids)

    for adapter in adapters:
        backend_name = getattr(adapter, "backend_name", type(adapter).__name__)
        started_backend = time.perf_counter()
        search_outputs: List[SearchOutput] = []
        all_items: List[RetrievalItem] = []
        try:
            adapter.reset_run(run_id)

            for conv in fixture.conversations:
                adapter.ingest_conversation(conv)

            # Search each question once at the largest requested k, then compute
            # metrics at every configured cutoff from the same ranked list. This
            # keeps adapter calls fair while enabling LOCOMO/LongMemEval-style
            # multi-cutoff reporting.
            top_k = int(max_top_k)
            for q in fixture.questions:
                out = adapter.search(query_id=q.question_id, query=q.query, top_k=top_k)
                search_outputs.append(out)
                all_items.extend(out.items)

            retrieval_by_k = _metrics_by_k(search_outputs, expected_map, top_k_values=normalized_top_k_values)
            metrics = {
                "retrieval": retrieval_by_k[str(top_k)],
                "retrieval_by_k": retrieval_by_k,
            }
            control_audit = _compute_control_audit(all_items)
            raw_cost_latency = adapter.export_cost_latency_stats()
            backend_wall_ms = (time.perf_counter() - started_backend) * 1000.0
            cost_latency = dict(raw_cost_latency)
            cost_latency["summary"] = _summarize_cost_latency(raw_cost_latency, backend_wall_ms=backend_wall_ms)

            backend_result = BackendResult(
                backend_name=backend_name,
                status="ok",
                status_reason=None,
                config_summary={"backend_name": backend_name},
                ingest={"conversation_count": len(fixture.conversations)},
                search={
                    "question_count": len(fixture.questions),
                    "top_k": top_k,
                    "top_k_values": list(normalized_top_k_values),
                    "latency_ms": [o.latency_ms for o in search_outputs],
                },
                metrics=metrics,
                retrieval_details=adapter.export_retrieval_details() if include_retrieval_details else None,
                cost_latency=cost_latency,
                control_audit=control_audit,
                errors=[],
            )
            report.backend_results.append(backend_result)
        except AdapterSkip as exc:
            report.backend_results.append(
                BackendResult(
                    backend_name=backend_name,
                    status="skipped",
                    status_reason=str(exc),
                    config_summary={"backend_name": backend_name},
                    ingest={},
                    search={},
                    metrics={},
                    retrieval_details=None,
                    cost_latency={},
                    control_audit={},
                    errors=[],
                )
            )
        except Exception as exc:  # pragma: no cover
            report.backend_results.append(
                BackendResult(
                    backend_name=backend_name,
                    status="failed",
                    status_reason=f"{type(exc).__name__}: {exc}",
                    config_summary={"backend_name": backend_name},
                    ingest={},
                    search={},
                    metrics={},
                    retrieval_details=None,
                    cost_latency={},
                    control_audit={},
                    errors=[repr(exc)],
                )
            )
        finally:
            try:
                adapter.close()
            except Exception:
                pass
            _ = time.perf_counter() - started_backend

    report.aggregate_metrics = _aggregate_backend_summaries(
        report.backend_results,
        timeout_seconds=int(fairness["timeout_seconds"]),
    )

    safe_path = _safe_write_path(output_path, repo_root=repo_root)
    report.write_json(safe_path)
    return report


def _git_sha_or_unknown(repo_root: Path) -> str:
    head = repo_root / ".git" / "HEAD"
    if not head.exists():
        return "unknown"
    try:
        head_text = head.read_text(encoding="utf-8").strip()
        if head_text.startswith("ref:"):
            ref_path = head_text.split(" ", 1)[1].strip()
            ref_file = repo_root / ".git" / ref_path
            if ref_file.exists():
                return ref_file.read_text(encoding="utf-8").strip()[:40]
            packed = repo_root / ".git" / "packed-refs"
            if packed.exists():
                for line in packed.read_text(encoding="utf-8").splitlines():
                    if line.startswith("#") or line.startswith("^") or not line.strip():
                        continue
                    sha, ref = line.split(" ", 1)
                    if ref.strip() == ref_path:
                        return sha.strip()[:40]
        # Detached HEAD
        if len(head_text) >= 7:
            return head_text[:40]
    except Exception:
        return "unknown"
    return "unknown"


__all__ = ["run_fixture_benchmark", "HarnessFairnessConfig"]
