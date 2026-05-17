from __future__ import annotations

import argparse
from pathlib import Path

from shyftr.benchmarks.adapters.no_memory import NoMemoryBackendAdapter
from shyftr.benchmarks.adapters.shyftr_backend import ShyftRBackendAdapter
from shyftr.benchmarks.fixture import resolve_benchmark_fixture
from shyftr.benchmarks.runner import run_fixture_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run ShyftR Phase 11 fixture-safe memory benchmark harness (P11-3: public-safe LOCOMO-mini fixture)."
    )
    parser.add_argument("--run-id", default="local-dev", help="Run identifier written into the report.")
    parser.add_argument(
        "--output",
        default="artifacts/benchmarks/memory_report.json",
        help="Output report path. Must be under artifacts/, reports/, or tmp/.",
    )
    parser.add_argument("--top-k", type=int, default=10, help="Top-k value for backend search.")
    parser.add_argument(
        "--include-retrieval-details",
        action="store_true",
        help="Include public-safe retrieval details in report (default false for smaller artifacts).",
    )

    parser.add_argument(
        "--fixture",
        default="synthetic-mini",
        choices=["synthetic-mini", "locomo-mini"],
        help="Fixture selector (default: synthetic-mini).",
    )
    parser.add_argument(
        "--fixture-path",
        default=None,
        help="Explicit fixture JSON path (overrides --fixture). Fixtures marked contains_private_data=true are rejected by default.",
    )
    parser.add_argument(
        "--allow-private-fixture",
        action="store_true",
        help="Allow loading fixtures with contains_private_data=true (local, non-public runs only).",
    )

    parser.add_argument(
        "--include-mem0-oss",
        action="store_true",
        help="Include the optional mem0 OSS/local backend adapter (default: off; skipped if mem0 not installed).",
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_path = (repo_root / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()

    fixture = resolve_benchmark_fixture(
        fixture_name=args.fixture,
        fixture_path=Path(args.fixture_path) if args.fixture_path else None,
        allow_private_data=bool(args.allow_private_fixture),
    )

    # Cell root is always under repo tmp/ for fixture-safe runs.
    cell_root = repo_root / "tmp" / "bench_cells" / args.run_id

    adapters = [
        ShyftRBackendAdapter(
            cell_root=cell_root,
            cell_id="bench-cell",
            trust_reason=f"fixture:{fixture.dataset_name}",
        ),
        NoMemoryBackendAdapter(),
    ]

    if bool(args.include_mem0_oss):
        # Import is local to keep optional dependency out of default path.
        from shyftr.benchmarks.adapters.mem0_backend import Mem0OSSBackendAdapter

        adapters.append(Mem0OSSBackendAdapter())

    run_fixture_benchmark(
        fixture=fixture,
        adapters=adapters,
        run_id=args.run_id,
        output_path=output_path,
        repo_root=repo_root,
        top_k_values=[args.top_k],
        include_retrieval_details=bool(args.include_retrieval_details),
        command_argv=None,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
