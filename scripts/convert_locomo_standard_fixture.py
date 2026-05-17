from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

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


def convert_locomo_standard_file(
    input_path: Path,
    output_path: Path,
    *,
    repo_root: Path,
    allow_private_input: bool = False,
    public_output: bool = False,
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

    safe_output.parent.mkdir(parents=True, exist_ok=True)
    safe_output.write_text(json.dumps(fixture.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    )
    print(str(written))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
