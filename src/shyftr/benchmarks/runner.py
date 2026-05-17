from __future__ import annotations

import json
import math
import platform
import signal
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from shyftr.benchmarks.adapters.base import AdapterSkip, BackendAdapter
from shyftr.benchmarks.answerer import build_answerer
from shyftr.benchmarks.fixture import BenchmarkFixture
from shyftr.benchmarks.judge import build_judge
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


class BenchmarkOperationTimeout(TimeoutError):
    """Raised when a benchmark adapter operation exceeds the configured budget."""


@contextmanager
def _operation_timeout(seconds: int):
    if seconds <= 0 or not hasattr(signal, "SIGALRM") or threading.current_thread() is not threading.main_thread():
        yield
        return

    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, 0)

    def _raise_timeout(_signum: int, _frame: Any) -> None:
        raise BenchmarkOperationTimeout(f"benchmark operation timed out after {seconds} seconds")

    signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, float(seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer and previous_timer[0] > 0:
            signal.setitimer(signal.ITIMER_REAL, previous_timer[0], previous_timer[1])


def _run_with_timeout(fn: Callable[[], Any], *, timeout_seconds: int) -> Any:
    with _operation_timeout(int(timeout_seconds)):
        return fn()


def _run_with_retries(
    fn: Callable[[], Any],
    *,
    timeout_seconds: int,
    max_retries: int,
    backend_name: str,
    operation: str,
    retry_events: List[Dict[str, Any]],
) -> Any:
    attempts_allowed = max(0, int(max_retries)) + 1
    for attempt_index in range(attempts_allowed):
        attempt_number = attempt_index + 1
        try:
            result = _run_with_timeout(fn, timeout_seconds=timeout_seconds)
            if attempt_index > 0:
                retry_events.append(
                    {
                        "backend_name": backend_name,
                        "operation": operation,
                        "attempt": attempt_number,
                        "status": "succeeded_after_retry",
                    }
                )
            return result
        except AdapterSkip:
            raise
        except Exception as exc:
            will_retry = attempt_number < attempts_allowed
            retry_events.append(
                {
                    "backend_name": backend_name,
                    "operation": operation,
                    "attempt": attempt_number,
                    "status": "retrying" if will_retry else "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            if not will_retry:
                raise
    raise RuntimeError("unreachable retry loop state")


def _summarize_retries(retry_events: Sequence[Dict[str, Any]], *, max_retries: int) -> Dict[str, Any]:
    retried_operations = sorted({str(event.get("operation")) for event in retry_events if event.get("status") in {"retrying", "succeeded_after_retry"}})
    return {
        "max_retries": max(0, int(max_retries)),
        "event_count": len(list(retry_events)),
        "retried_operation_count": len(retried_operations),
        "retried_operations": retried_operations,
        "events": [dict(event) for event in retry_events],
    }


def _backend_result_from_dict(payload: Dict[str, Any]) -> BackendResult:
    return BackendResult(
        backend_name=str(payload.get("backend_name", "unknown")),
        status=str(payload.get("status", "failed")),
        status_reason=payload.get("status_reason"),
        config_summary=dict(payload.get("config_summary", {})),
        ingest=dict(payload.get("ingest", {})),
        search=dict(payload.get("search", {})),
        metrics=dict(payload.get("metrics", {})),
        retrieval_details=payload.get("retrieval_details"),
        cost_latency=dict(payload.get("cost_latency", {})),
        control_audit=dict(payload.get("control_audit", {})),
        errors=list(payload.get("errors", [])),
    )


def _load_resumable_backend_results(output_path: Path, *, run_id: str, fixture: BenchmarkFixture) -> Dict[str, BackendResult]:
    if not output_path.exists():
        return {}
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    dataset = dict(payload.get("dataset", {}))
    if payload.get("run_id") != run_id:
        return {}
    if dataset.get("name") != fixture.dataset_name or dataset.get("version") != fixture.dataset_version or dataset.get("split") != fixture.fixture_id:
        return {}

    resumable: Dict[str, BackendResult] = {}
    for raw in payload.get("backend_results", []):
        result = _backend_result_from_dict(dict(raw))
        if result.status in {"ok", "skipped"}:
            resumable[result.backend_name] = result
    return resumable


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
    ndcg_sum = 0.0
    supported_questions = 0

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
        dcg = 0.0
        for rank, rid in enumerate(returned_ids, start=1):
            if rid in expected:
                dcg += 1.0 / math.log2(rank + 1)
                rr = 1.0 / float(rank)
                break
        ideal_relevant = min(len(set(expected)), k)
        idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_relevant + 1))

        if relevant_returned:
            supported_questions += 1

        recall_sum += recall
        precision_sum += precision
        mrr_sum += rr
        ndcg_sum += (dcg / idcg) if idcg else 0.0

    if total_questions == 0:
        return {
            "question_count": 0,
            "recall_at_k": None,
            "precision_at_k": None,
            "mrr": None,
            "ndcg_at_k": None,
            "answer_support_coverage": "not_supported",
            "conflict_retrieval_rate": "not_supported",
            "stale_retrieval_rate": "not_supported",
        }

    return {
        "question_count": total_questions,
        "recall_at_k": recall_sum / total_questions,
        "precision_at_k": precision_sum / total_questions,
        "mrr": mrr_sum / total_questions,
        "ndcg_at_k": ndcg_sum / total_questions,
        "answer_support_coverage": supported_questions / total_questions,
        "conflict_retrieval_rate": "not_supported",
        "stale_retrieval_rate": "not_supported",
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


def _aggregate_backend_summaries(backend_results: Sequence[BackendResult], *, timeout_seconds: int, resumed_backends: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    status_counts: Dict[str, int] = {}
    cost_latency_by_backend: Dict[str, Any] = {}
    timeout_failures: List[str] = []
    retry_events_by_backend: Dict[str, Any] = {}

    for result in backend_results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
        cost_latency_by_backend[result.backend_name] = result.cost_latency.get("summary", {}) if result.cost_latency else {}
        retry_events_by_backend[result.backend_name] = result.cost_latency.get("retry_summary", {}) if result.cost_latency else {}
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
            "timeout_enforcement": "hard_signal_alarm" if hasattr(signal, "SIGALRM") else "not_available",
        },
        "resume_summary": {
            "resumed_backend_count": len(list(resumed_backends or [])),
            "resumed_backends": list(resumed_backends or []),
        },
        "retry_summary": {
            "backends": retry_events_by_backend,
            "backend_count_with_retry_events": sum(1 for summary in retry_events_by_backend.values() if summary.get("event_count", 0)),
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



def _compute_answer_eval(
    *,
    fixture: BenchmarkFixture,
    search_outputs: Sequence[SearchOutput],
    answerer_name: str,
    judge_name: str,
) -> Dict[str, Any]:
    answerer = build_answerer(answerer_name)
    judge = build_judge(judge_name)
    by_question = {q.question_id: q for q in fixture.questions}
    results: List[Dict[str, Any]] = []
    by_type: Dict[str, Dict[str, Any]] = {}
    correct = correct_abstention = missed = unsupported = abstained = 0
    f1_values: List[float] = []

    for out in search_outputs:
        question = by_question.get(out.query_id)
        if question is None:
            continue
        answer = answerer.answer(question=question, retrieved_items=out.items)
        judged = judge.judge(question=question, answer=answer)
        if judged.verdict in {"correct", "partially_correct"}:
            correct += 1
        if judged.verdict == "correct_abstention":
            correct_abstention += 1
        if judged.verdict == "missed_answer":
            missed += 1
        if judged.verdict == "unsupported_answer":
            unsupported += 1
        if answer.answer_state.startswith("abstained"):
            abstained += 1
        if judged.token_f1 is not None:
            f1_values.append(float(judged.token_f1))
        label = question.question_type or "unknown"
        bucket = by_type.setdefault(label, {"question_count": 0, "correct": 0, "missed_answer": 0, "unsupported_answer": 0})
        bucket["question_count"] += 1
        if judged.verdict in {"correct", "partially_correct"}:
            bucket["correct"] += 1
        if judged.verdict == "missed_answer":
            bucket["missed_answer"] += 1
        if judged.verdict == "unsupported_answer":
            bucket["unsupported_answer"] += 1
        results.append({"query_id": out.query_id, "answer": answer.to_dict(), "judge": judged.to_dict()})

    total = len(results)
    return {
        "enabled": True,
        "answerer": getattr(answerer, "name", answerer_name),
        "judge": getattr(judge, "name", judge_name),
        "question_count": total,
        "correctness": (correct / total) if total else None,
        "token_f1": (sum(f1_values) / len(f1_values)) if f1_values else None,
        "abstention_rate": (abstained / total) if total else None,
        "correct_abstention_rate": (correct_abstention / total) if total else None,
        "missed_answer_rate": (missed / total) if total else None,
        "unsupported_answer_rate": (unsupported / total) if total else None,
        "by_question_type": by_type,
        "results": results,
        "claim_limit": "fixture-level runner-owned deterministic answer evaluation only; not a standard-dataset answer-quality claim",
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
    runner_version: str = "phase11-p11-4c",
    command_argv: Optional[List[str]] = None,
    timeout_seconds: int = 60,
    max_retries: int = 0,
    resume_existing: bool = False,
    enable_answer_eval: bool = False,
    answerer_name: str = "deterministic-extractive",
    judge_name: str = "deterministic-composite",
) -> BenchmarkReport:
    normalized_top_k_values = _normalize_top_k_values(top_k_values)
    max_top_k = max(normalized_top_k_values)
    fairness = HarnessFairnessConfig(
        top_k_values=list(normalized_top_k_values),
        timeout_seconds=int(timeout_seconds),
        max_retries=int(max_retries),
        answerer_owned_by_runner=bool(enable_answer_eval),
        judge_owned_by_runner=bool(enable_answer_eval),
    ).to_dict()

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
        "answerer": {"name": str(answerer_name) if enable_answer_eval else "runner-owned-disabled", "version": "phase12-v0" if enable_answer_eval else None},
        "judge": {"name": str(judge_name) if enable_answer_eval else "runner-owned-disabled", "version": "phase12-v0" if enable_answer_eval else None},
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
            "Answerer/judge are runner-owned and deterministic when enabled; no external LLM calls are made.",
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

    safe_path = _safe_write_path(output_path, repo_root=repo_root)
    resumable_results = _load_resumable_backend_results(safe_path, run_id=run_id, fixture=fixture) if resume_existing else {}
    resumed_backend_names: List[str] = []

    expected_map: Dict[str, List[str]] = {}
    for q in fixture.questions:
        if q.expected_item_ids:
            expected_map[q.question_id] = list(q.expected_item_ids)

    for adapter in adapters:
        backend_name = getattr(adapter, "backend_name", type(adapter).__name__)
        if backend_name in resumable_results:
            report.backend_results.append(resumable_results[backend_name])
            resumed_backend_names.append(backend_name)
            continue

        started_backend = time.perf_counter()
        search_outputs: List[SearchOutput] = []
        all_items: List[RetrievalItem] = []
        retry_events: List[Dict[str, Any]] = []
        try:
            _run_with_retries(
                lambda: adapter.reset_run(run_id),
                timeout_seconds=int(timeout_seconds),
                max_retries=int(max_retries),
                backend_name=backend_name,
                operation="reset_run",
                retry_events=retry_events,
            )

            for conv in fixture.conversations:
                _run_with_retries(
                    lambda conv=conv: adapter.ingest_conversation(conv),
                    timeout_seconds=int(timeout_seconds),
                    max_retries=int(max_retries),
                    backend_name=backend_name,
                    operation=f"ingest:{conv.conversation_id}",
                    retry_events=retry_events,
                )

            # Search each question once at the largest requested k, then compute
            # metrics at every configured cutoff from the same ranked list. This
            # keeps adapter calls fair while enabling LOCOMO/LongMemEval-style
            # multi-cutoff reporting.
            top_k = int(max_top_k)
            for q in fixture.questions:
                out = _run_with_retries(
                    lambda q=q: adapter.search(query_id=q.question_id, query=q.query, top_k=top_k),
                    timeout_seconds=int(timeout_seconds),
                    max_retries=int(max_retries),
                    backend_name=backend_name,
                    operation=f"search:{q.question_id}",
                    retry_events=retry_events,
                )
                search_outputs.append(out)
                all_items.extend(out.items)

            retrieval_by_k = _metrics_by_k(search_outputs, expected_map, top_k_values=normalized_top_k_values)
            metrics = {
                "retrieval": retrieval_by_k[str(top_k)],
                "retrieval_by_k": retrieval_by_k,
            }
            if enable_answer_eval:
                metrics["answer_eval"] = _compute_answer_eval(
                    fixture=fixture,
                    search_outputs=search_outputs,
                    answerer_name=answerer_name,
                    judge_name=judge_name,
                )
            else:
                metrics["answer_eval"] = {"enabled": False, "reason": "enable_answer_eval flag not set"}
            control_audit = _compute_control_audit(all_items)
            raw_cost_latency = adapter.export_cost_latency_stats()
            backend_wall_ms = (time.perf_counter() - started_backend) * 1000.0
            cost_latency = dict(raw_cost_latency)
            cost_latency["summary"] = _summarize_cost_latency(raw_cost_latency, backend_wall_ms=backend_wall_ms)
            cost_latency["retry_summary"] = _summarize_retries(retry_events, max_retries=int(max_retries))

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
                    cost_latency={"retry_summary": _summarize_retries(retry_events, max_retries=int(max_retries))},
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
        resumed_backends=resumed_backend_names,
    )

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
