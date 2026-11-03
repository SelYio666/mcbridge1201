#!/usr/bin/env python3
"""Manifest coverage guard: every tracked run evidence doc/result must be hashed.

`check_hashes.py` verifies the files the manifest lists; it cannot notice a tracked file that
was never added to the list. This guard closes that hole for the two files each run must ship:
`runs/*/README.md` and `runs/*/result.json`.

Also reports manifest entries that are not tracked (a fresh clone could not check them).
Exit code 0 when clean, 1 otherwise. Runs on the working tree, matching what CI checks out.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "runs" / "SHA256SUMS.txt"
REQUIRED_SUFFIXES = ("/README.md", "/result.json")


def tracked_runs_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z", "runs/"], cwd=ROOT,
                         capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def manifest_entries() -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if "  " in line:
            digest, path = line.split("  ", 1)
            entries[path] = digest
    return entries


def main() -> int:
    tracked = tracked_runs_files()
    tracked_set = set(tracked)
    manifest = manifest_entries()
    required = [p for p in tracked
                if p.endswith(REQUIRED_SUFFIXES) and not p.endswith("runs/SHA256SUMS.txt")]
    missing = sorted(p for p in required if p not in manifest)
    untracked = sorted(p for p in manifest if p.startswith("runs/") and p not in tracked_set)

    print(f"tracked runs files: {len(tracked)}")
    print(f"required evidence files: {len(required)}")
    print(f"hashed evidence files: {len(required) - len(missing)}")
    for p in missing[:20]:
        print("MISSING FROM MANIFEST:", p)
    for p in untracked[:20]:
        print("MANIFEST ENTRY NOT TRACKED:", p)
    if missing or untracked:
        print(f"\ncoverage FAILED: {len(missing)} missing, {len(untracked)} untracked")
        return 1
    print("\ncoverage OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
