#!/usr/bin/env python3
"""Dependency-free checks for the publication package itself."""
from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "README.md",
    "ARTIFACT_MANIFEST.json",
    "CITATION.cff",
    "docs/REPOSITORY_AUDIT.md",
    "docs/PAPER_CLAIM_MATRIX.csv",
    "docs/PAPER_CLAIM_AUDIT.md",
    "docs/ISCOPE_ADAPTATION_AUDIT.md",
    "docs/METRIC_AUDIT.md",
    "provenance/RESULT_PROVENANCE.csv",
    "src/main/java/edu/ipcmax/core/pcmax/PACE.java",
    "src/test/java/edu/ipcmax/testoracle/PaceExactOracleDifferentialTest.java",
)


def main() -> int:
    failures: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            failures.append(f"missing required file: {relative}")

    forbidden_parts = {".venv", "__pycache__", "target", "raw"}
    for path in ROOT.rglob("*"):
        if any(part in forbidden_parts for part in path.parts):
            failures.append(f"forbidden generated/private path: {path.relative_to(ROOT)}")
        if path.is_file() and path.suffix.lower() in {".zip", ".jar", ".class"}:
            failures.append(f"unnecessary binary: {path.relative_to(ROOT)}")

    absolute = re.compile(r"(?:/home/|/Users/|(?<![A-Za-z])[A-Za-z]:[\\/])")
    for path in ROOT.rglob("*"):
        if path == Path(__file__).resolve() or not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if absolute.search(text):
            failures.append(f"machine-specific absolute path: {path.relative_to(ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"integrity=PASS files={sum(1 for p in ROOT.rglob('*') if p.is_file())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
