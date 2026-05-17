"""Benchmark harness components (Phase 11).

This package is intentionally dependency-light and fixture-safe. It exists to
validate adapter and report contracts before any large third-party datasets are
introduced.
"""

from .fixture import BenchmarkFixture
from .report import BenchmarkReport

__all__ = ["BenchmarkFixture", "BenchmarkReport"]
