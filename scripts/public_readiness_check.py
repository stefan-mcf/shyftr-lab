#!/usr/bin/env python3
"""Local public-readiness checks for the ShyftR repo."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "pyproject.toml",
    "docs/status/current-implementation-status.md",
    "docs/status/release-readiness.md",
    "docs/status/public-readiness-audit.md",
    "docs/development.md",
    "docs/api.md",
    "docs/console.md",
    "examples/README.md",
    "examples/run-local-lifecycle.sh",
    "scripts/release_gate.sh",
    "scripts/alpha_gate.sh",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    ".github/pull_request_template.md",
]
README_SECTIONS = [
    "Current status",
    "Install from clone",
    "Release readiness gate",
    "Quickstart",
    "Safety model",
    "Architecture",
    "Documentation",
    "Development checks",
    "License",
]
BANNED_README = [
    "production-ready",
    "enterprise-grade",
    "ALPHA_GATE_READY",
    "controlled-pilot",
    "developer preview",
]
PRIVATE_PATTERNS = [
    re.compile(r"/(Users|home)/[^\s`)\]}>\"']+"),
    re.compile(r"stefan@example\.com"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
]
PUBLIC_PREFIXES = (
    "docs/",
    "examples/",
    ".github/",
    "scripts/",
)
PUBLIC_FILES = {
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "pyproject.toml",
}
PRIVATE_PATTERN_SOURCE_ALLOWLIST = {
    "scripts/public_readiness_check.py",
}
ALLOW_UNTRACKED_PREFIXES = {".hermes/"}
RISKY_UNTRACKED = re.compile(r"(\.env|auth\.json|MEMORY\.md|USER\.md|state\.db|\.sqlite|\.sqlite3|\.db|\.pem|\.key|id_rsa|id_ed25519|\.tar\.gz)$", re.I)


def run_git(*args: str) -> list[str]:
    proc = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True)
    return [line for line in proc.stdout.splitlines() if line]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def public_files() -> list[Path]:
    out: list[Path] = []
    for rel in run_git("ls-files"):
        if rel in PUBLIC_FILES or rel.startswith(PUBLIC_PREFIXES):
            out.append(ROOT / rel)
    return sorted(set(out))


def allowed_private_pattern_match(rel: str, line: str) -> bool:
    if rel in PRIVATE_PATTERN_SOURCE_ALLOWLIST and "re.compile" in line:
        return True
    return False


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            fail(errors, f"missing required file: {rel}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    low = readme.lower()
    for section in README_SECTIONS:
        if section.lower() not in low:
            fail(errors, f"README missing section: {section}")
    for banned in BANNED_README:
        if banned.lower() in low:
            fail(errors, f"README contains banned phrase: {banned}")
    if "stable local-first" not in low:
        fail(errors, "README missing stable local-first release posture")
    for banned_public_planning_term in ["phase", "roadmap"]:
        if banned_public_planning_term in low:
            fail(errors, f"README contains internal planning term: {banned_public_planning_term}")
    if "what is deliberately out of scope" not in low:
        fail(errors, "README missing explicit out-of-scope section")
    if "hosted platform operation" not in low or "multi-tenant deployment" not in low:
        fail(errors, "README missing hosted/multi-tenant out-of-scope boundary")
    if "SHYFTR_RELEASE_READY" not in readme:
        fail(errors, "README missing release gate expected verdict")

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if "Development Status :: 5 - Production/Stable" not in pyproject:
        fail(errors, "pyproject missing stable development-status classifier")

    release_doc = (ROOT / "docs" / "status" / "release-readiness.md").read_text(encoding="utf-8").lower()
    for phrase in ["stable local-first", "synthetic data", "hosted platform operation", "multi-tenant deployment", "release_gate.sh"]:
        if phrase not in release_doc:
            fail(errors, f"release-readiness doc missing required phrase: {phrase}")

    for rel in ["README.md", "CONTRIBUTING.md", "docs/status/release-readiness.md", "docs/status/current-implementation-status.md"]:
        text = (ROOT / rel).read_text(encoding="utf-8").lower()
        for banned_public_planning_term in ["phase", "roadmap"]:
            if banned_public_planning_term in text:
                fail(errors, f"public-facing doc contains internal planning term {banned_public_planning_term}: {rel}")
    tracked = set(run_git("ls-files"))
    if any(p.startswith(".hermes/") for p in tracked):
        fail(errors, ".hermes/ is tracked")

    ignored_tracked = run_git("ls-files", "-ci", "--exclude-standard")
    if ignored_tracked:
        fail(errors, "tracked files match ignore rules: " + ", ".join(ignored_tracked[:10]))

    untracked = run_git("ls-files", "--others", "--exclude-standard")
    risky = [p for p in untracked if RISKY_UNTRACKED.search(p) and not any(p.startswith(a) for a in ALLOW_UNTRACKED_PREFIXES)]
    if risky:
        fail(errors, "risky nonignored untracked files: " + ", ".join(risky[:10]))

    for path in [ROOT / "examples" / "task.json", ROOT / "examples" / "integrations" / "task-request.json", ROOT / "examples" / "integrations" / "feedback-report.json"]:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(errors, f"invalid JSON example {path.relative_to(ROOT)}: {exc}")

    yaml_paths = list((ROOT / "examples").rglob("*.yaml")) + list((ROOT / "examples").rglob("*.yml"))
    if yaml is None and yaml_paths:
        warnings.append("PyYAML unavailable; YAML examples not parsed")
    elif yaml is not None:
        for path in yaml_paths:
            try:
                yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception as exc:
                fail(errors, f"invalid YAML example {path.relative_to(ROOT)}: {exc}")

    for script_rel in ["examples/run-local-lifecycle.sh", "scripts/release_gate.sh", "scripts/alpha_gate.sh"]:
        script = ROOT / script_rel
        if not script.exists() or not (script.stat().st_mode & 0o111):
            fail(errors, f"{script_rel} missing or not executable")

    for path in public_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(ROOT).as_posix()
        for lineno, line in enumerate(text.splitlines(), 1):
            for pat in PRIVATE_PATTERNS:
                if pat.search(line) and not allowed_private_pattern_match(rel, line):
                    fail(errors, f"private/secret pattern in current public file: {rel}:{lineno}: {pat.pattern}")

    print("ShyftR public readiness check")
    for warning in warnings:
        print(f"WARN: {warning}")
    if errors:
        print("FAIL")
        for err in errors:
            print(f"- {err}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
