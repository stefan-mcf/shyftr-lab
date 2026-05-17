from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

from .ledger import append_jsonl, read_jsonl
from .ledger_state import latest_by_key, latest_record_by_key
from .models import Episode

PathLike = Union[str, Path]

EPISODES_LEDGER = Path("ledger") / "episodes.jsonl"


def _anchor_list(value: Optional[Sequence[Any] | Mapping[str, Any] | str], field_name: str, *, allow_mapping: bool = False) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        if not allow_mapping:
            raise ValueError(f"{field_name} entries must be strings")
        return [dict(value)]
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        items = list(value)
        if not allow_mapping and any(isinstance(item, Mapping) for item in items):
            raise ValueError(f"{field_name} entries must be strings")
        return items
    raise ValueError(f"{field_name} must be a string, object, or list")


def _episode_terms(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _now_fallback(value: Optional[str] = None) -> str:
    if value:
        return value
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _read_cell_id(cell_path: PathLike) -> str:
    cell = Path(cell_path)
    for manifest_path in (cell / "config" / "cell_manifest.json", cell / "manifest.json"):
        if manifest_path.exists():
            return str(json.loads(manifest_path.read_text(encoding="utf-8")).get("cell_id") or cell.name)
    return cell.name


def _read_cell_type(cell_path: PathLike) -> str:
    cell = Path(cell_path)
    for manifest_path in (cell / "config" / "cell_manifest.json", cell / "manifest.json"):
        if manifest_path.exists():
            return str(json.loads(manifest_path.read_text(encoding="utf-8")).get("cell_type") or "")
    return ""


def _episode_public_capsule(episode: Episode, *, reveal_private: bool = False) -> Dict[str, Any]:
    redact_prose = episode.status == "redacted" or (episode.sensitivity in {"private", "secret", "restricted"} and not reveal_private)
    return {
        "episode_id": episode.episode_id,
        "memory_id": episode.episode_id,
        "memory_type": "episodic",
        "episode_kind": episode.episode_kind,
        "title": None if redact_prose else episode.title,
        "summary": None if redact_prose else episode.summary,
        "outcome": episode.outcome,
        "status": episode.status,
        "started_at": episode.started_at,
        "ended_at": episode.ended_at,
        "confidence": episode.confidence,
        "sensitivity": episode.sensitivity,
        "anchors": {
            "live_context_entry_ids": list(episode.live_context_entry_ids),
            "memory_ids": list(episode.memory_ids),
            "feedback_ids": list(episode.feedback_ids),
            "resource_refs": [ref.to_dict() for ref in episode.resource_refs],
            "grounding_refs": list(episode.grounding_refs),
            "artifact_refs": list(episode.artifact_refs),
        },
    }


def make_episode(
    cell_path: PathLike,
    *,
    episode_id: str,
    episode_kind: str,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    outcome: str = "unknown",
    status: str = "proposed",
    started_at: Optional[str] = None,
    ended_at: Optional[str] = None,
    confidence: Optional[float] = 0.8,
    sensitivity: str = "internal",
    runtime_id: Optional[str] = None,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    live_context_entry_ids: Optional[Sequence[str]] = None,
    memory_ids: Optional[Sequence[str]] = None,
    feedback_ids: Optional[Sequence[str]] = None,
    resource_refs: Optional[Sequence[Any]] = None,
    grounding_refs: Optional[Sequence[str]] = None,
    artifact_refs: Optional[Sequence[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    provided_fields: Optional[Sequence[str]] = None,
) -> Episode:
    now = _now_fallback()
    cell_type = _read_cell_type(cell_path)
    if cell_type != "memory":
        raise ValueError(f"episodes can only be written to memory cells, got {cell_type!r}")
    episode_payload: Dict[str, Any] = dict(
        episode_id=episode_id,
        cell_id=_read_cell_id(cell_path),
        episode_kind=episode_kind,
        title=title,
        summary=summary,
        started_at=started_at,
        ended_at=ended_at,
        actor=actor,
        action=action,
        outcome=outcome,
        status=status,
        confidence=confidence,
        sensitivity=sensitivity,
        created_at=now,
        runtime_id=runtime_id,
        session_id=session_id,
        task_id=task_id,
        live_context_entry_ids=_anchor_list(live_context_entry_ids, "live_context_entry_ids"),
        memory_ids=_anchor_list(memory_ids, "memory_ids"),
        feedback_ids=_anchor_list(feedback_ids, "feedback_ids"),
        resource_refs=_anchor_list(resource_refs, "resource_refs", allow_mapping=True),
        grounding_refs=_anchor_list(grounding_refs, "grounding_refs"),
        artifact_refs=_anchor_list(artifact_refs, "artifact_refs"),
        metadata=dict(metadata or {}),
    )
    latest = get_latest_episode(cell_path, episode_id)
    if latest is not None:
        merged = latest.to_dict()
        provided = set(provided_fields) if provided_fields is not None else None
        default_values = {"episode_kind": "session", "outcome": "unknown", "sensitivity": "internal", "confidence": 0.8}
        for key, value in episode_payload.items():
            if key == "status" and value == "proposed" and merged.get("status") != "proposed":
                continue
            if key in {"status", "created_at"}:
                merged[key] = value
            elif provided is not None and key not in provided and key in default_values and value == default_values[key] and merged.get(key) is not None:
                continue
            elif provided is not None and key in provided:
                merged[key] = value
            elif value not in (None, "", [], {}):
                merged[key] = value
        if merged.get("status") == "redacted":
            for field_name in ("title", "summary", "failure_signature", "recovery_summary"):
                merged[field_name] = None
            merged["key_points"] = []
        episode_payload = merged
    if episode_payload.get("status") == "redacted":
        for field_name in ("title", "summary", "failure_signature", "recovery_summary"):
            episode_payload[field_name] = None
        episode_payload["key_points"] = []
    return Episode(**episode_payload)


def capture_episode(cell_path: PathLike, episode: Episode, *, write: bool = False) -> Dict[str, Any]:
    status = "ok" if write else "dry_run"
    if write:
        append_episode(cell_path, episode)
    return {"status": status, "write": bool(write), "episode": episode.to_dict(), "capsule": _episode_public_capsule(episode)}


def search_episode_capsules(cell_path: PathLike, query: str, *, limit: int = 10, include_private: bool = False) -> List[Dict[str, Any]]:
    terms = _episode_terms(query)
    scored_capsules: List[Tuple[int, int, Dict[str, Any]]] = []
    for index, episode in enumerate(list_latest_episodes(cell_path)):
        if episode.status in {"proposed", "rejected", "superseded"}:
            continue
        if not include_private and episode.sensitivity in {"private", "secret", "restricted"}:
            continue
        searchable_prose = () if episode.status == "redacted" or episode.sensitivity in {"private", "secret", "restricted"} else (episode.title, episode.summary)
        haystack = " ".join(str(part or "") for part in (episode.episode_id, *searchable_prose, episode.outcome, episode.status, episode.episode_kind)).lower()
        haystack_terms = _episode_terms(haystack)
        score = len(terms & haystack_terms) if terms else 0
        if terms and score <= 0:
            continue
        scored_capsules.append((score, index, _episode_public_capsule(episode, reveal_private=include_private)))
    scored_capsules.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [capsule for _, _, capsule in scored_capsules[: max(limit, 0)]]


def episodes_ledger_path(cell_path: PathLike) -> Path:
    return Path(cell_path) / EPISODES_LEDGER


def append_episode(cell_path: PathLike, episode: Episode) -> Episode:
    """Append an Episode row to the additive episode ledger."""
    cell_type = _read_cell_type(cell_path)
    if cell_type != "memory":
        raise ValueError(f"episodes can only be written to memory cells, got {cell_type!r}")
    expected_cell_id = _read_cell_id(cell_path)
    if episode.cell_id != expected_cell_id:
        raise ValueError(f"episode cell_id {episode.cell_id!r} does not match target cell {expected_cell_id!r}")
    latest = get_latest_episode(cell_path, episode.episode_id)
    post_approval_statuses = {"archived", "redacted", "superseded"}
    if latest is None and episode.status in post_approval_statuses:
        raise ValueError(f"cannot write {episode.status!r} episode {episode.episode_id!r} without an approved predecessor")
    if latest is None and episode.status == "rejected":
        raise ValueError(f"cannot reject episode {episode.episode_id!r} without a proposal predecessor")
    if latest is not None and latest.status not in {"proposed", "rejected"} and episode.status in {"proposed", "rejected"}:
        raise ValueError(f"cannot regress episode {episode.episode_id!r} from {latest.status!r} to {episode.status!r}")
    if latest is not None and latest.status in {"rejected", "archived", "redacted", "superseded"} and episode.status != latest.status:
        raise ValueError(f"cannot transition terminal episode {episode.episode_id!r} from {latest.status!r} to {episode.status!r}")
    if latest is not None and episode.status in post_approval_statuses and latest.status in {"proposed", "rejected"}:
        raise ValueError(f"cannot transition episode {episode.episode_id!r} from {latest.status!r} to {episode.status!r}")
    append_jsonl(episodes_ledger_path(cell_path), episode.to_dict())
    return episode


def propose_episode(cell_path: PathLike, episode: Episode) -> Episode:
    """Append a proposed Episode row."""
    if episode.status != "proposed":
        raise ValueError("propose_episode requires status=proposed")
    return append_episode(cell_path, episode)


def approve_episode(cell_path: PathLike, episode: Episode) -> Episode:
    """Append an approved Episode row.

    Episode validation enforces that approved rows carry at least one anchor.
    """
    if episode.status != "approved":
        raise ValueError("approve_episode requires status=approved")
    latest = get_latest_episode(cell_path, episode.episode_id)
    if latest is not None:
        merged = latest.to_dict()
        for key, value in episode.to_dict().items():
            if key in {"status", "created_at"} or value not in (None, "", [], {}):
                merged[key] = value
        episode = Episode.from_dict(merged)
    return append_episode(cell_path, episode)


def read_episode_rows(cell_path: PathLike) -> Iterator[Tuple[int, Episode]]:
    """Yield episode ledger rows as validated Episode objects."""
    path = episodes_ledger_path(cell_path)
    if not path.exists():
        return
    for line_number, record in read_jsonl(path):
        yield line_number, Episode.from_dict(record)


def list_episode_rows(cell_path: PathLike) -> List[Episode]:
    return [episode for _, episode in read_episode_rows(cell_path)]


def list_latest_episodes(cell_path: PathLike) -> List[Episode]:
    records = [episode.to_dict() for episode in list_episode_rows(cell_path)]
    return [Episode.from_dict(record) for record in latest_by_key(records, "episode_id")]


def get_latest_episode(cell_path: PathLike, episode_id: str) -> Episode | None:
    records = [episode.to_dict() for episode in list_episode_rows(cell_path)]
    record = latest_record_by_key(records, "episode_id", episode_id)
    if record is None:
        return None
    return Episode.from_dict(record)
