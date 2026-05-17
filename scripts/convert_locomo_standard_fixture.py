from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from shyftr.benchmarks.locomo_standard import load_locomo_standard_json, map_locomo_standard_payload


_ALLOWED_OUTPUT_DIRS = ("artifacts", "reports", "tmp")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_output_path(output_path: Path, *, repo_root: Path) -> Path:
    resolved = Path(output_path).expanduser().resolve()
    allowed_roots = [(repo_root / name).resolve() for name in _ALLOWED_OUTPUT_DIRS]
    if not any(_is_relative_to(resolved, allowed_root) for allowed_root in allowed_roots):
        allowed = ", ".join(_ALLOWED_OUTPUT_DIRS)
        raise ValueError(f"Refusing to write converted fixture outside repo-local {allowed}/ directories: {resolved}")
    if resolved.suffix != ".json":
        raise ValueError(f"Converted fixture output must be a .json file: {resolved}")
    return resolved


def _read_json_or_jsonl(path: Path) -> Dict[str, Any]:
    resolved = Path(path).expanduser().resolve()
    if resolved.suffix == ".jsonl":
        rows = []
        with resolved.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if text:
                    rows.append(json.loads(text))
        return {"dataset_version": "jsonl-local", "split": resolved.stem, "contains_private_data": True, "conversations": rows}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return dict(payload) if isinstance(payload, dict) else {"contains_private_data": True, "conversations": payload}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).expanduser().resolve().open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_path_for(output_path: Path) -> Path:
    return output_path.with_suffix(output_path.suffix + ".manifest.json")


def _write_conversion_manifest(
    *,
    input_path: Path,
    output_path: Path,
    fixture_payload: Dict[str, Any],
    public_output: bool,
    allow_private_input: bool,
    manifest_path: Optional[Path] = None,
) -> Path:
    manifest = {
        "schema_version": "shyftr-memory-benchmark-conversion-manifest/v0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input_path": str(Path(input_path).expanduser().resolve()),
        "input_sha256": _sha256_file(input_path),
        "output_path": str(Path(output_path).expanduser().resolve()),
        "output_sha256": _sha256_file(output_path),
        "dataset_name": fixture_payload.get("dataset_name"),
        "dataset_version": fixture_payload.get("dataset_version"),
        "fixture_id": fixture_payload.get("fixture_id"),
        "contains_private_data": bool(fixture_payload.get("contains_private_data")),
        "conversation_count": len(fixture_payload.get("conversations") or []),
        "question_count": len(fixture_payload.get("questions") or []),
        "public_output": bool(public_output),
        "allow_private_input": bool(allow_private_input),
        "claim_limit": "conversion metadata only; not a full LOCOMO run or performance claim",
    }
    path = Path(manifest_path).expanduser().resolve() if manifest_path else _manifest_path_for(Path(output_path).expanduser().resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def convert_locomo_standard_file(
    input_path: Path,
    output_path: Path,
    *,
    repo_root: Path,
    allow_private_input: bool = False,
    public_output: bool = False,
    write_manifest: bool = True,
) -> Path:
    safe_output = _safe_output_path(output_path, repo_root=repo_root)

    if public_output:
        fixture = load_locomo_standard_json(input_path, allow_private_data=False)
    else:
        payload = _read_json_or_jsonl(input_path)
        if not allow_private_input and bool(payload.get("contains_private_data", True)):
            raise ValueError(
                "Refusing to convert LOCOMO-standard input marked or defaulted contains_private_data=true "
                "without --allow-private-input"
            )
        fixture = map_locomo_standard_payload(payload)

    if public_output and fixture.contains_private_data:
        raise ValueError("Refusing --public-output for a fixture marked contains_private_data=true")

    fixture_payload = fixture.to_dict()
    safe_output.parent.mkdir(parents=True, exist_ok=True)
    safe_output.write_text(json.dumps(fixture_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if write_manifest:
        _write_conversion_manifest(
            input_path=input_path,
            output_path=safe_output,
            fixture_payload=fixture_payload,
            public_output=public_output,
            allow_private_input=allow_private_input,
        )
    return safe_output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a local normalized LOCOMO-style JSON/JSONL file into a guarded ShyftR benchmark fixture. Does not download data."
    )
    parser.add_argument("--input", required=True, help="Local normalized LOCOMO-style JSON or JSONL input path.")
    parser.add_argument("--output", required=True, help="Output fixture JSON path under artifacts/, reports/, or tmp/.")
    parser.add_argument(
        "--allow-private-input",
        action="store_true",
        help="Allow conversion when the input is private-marked or lacks contains_private_data=false. Output remains local-only.",
    )
    parser.add_argument(
        "--public-output",
        action="store_true",
        help="Require contains_private_data=false and write a public-safe fixture JSON. Does not override output path guards.",
    )
    parser.add_argument(
        "--no-manifest",
        action="store_true",
        help="Do not write the default .manifest.json sidecar. Intended only for scratch debugging.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path

    written = convert_locomo_standard_file(
        Path(args.input),
        output_path,
        repo_root=repo_root,
        allow_private_input=bool(args.allow_private_input),
        public_output=bool(args.public_output),
        write_manifest=not bool(args.no_manifest),
    )
    print(str(written))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
