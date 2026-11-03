#!/usr/bin/env python3
"""One-command release check: the gates a release must pass, plus an optional portable build.

Usage:
    python tools/release_check.py                 # gates only
    python tools/release_check.py --build 0.5.11  # gates, then build dist/mcbridge-launcher-0.5.11.zip
    python tools/release_check.py --json out.json

Exit code 0 only when every step passes. This is the checklist that used to live only in docs
(`docs/handover-zcode.md`); keeping it executable means a release can't skip a gate by memory.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run(name: str, args: list[str], timeout: int = 1800) -> dict:
    start = time.time()
    proc = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    tail = [line for line in (proc.stdout or "").splitlines() if line.strip()][-3:]
    return {"name": name, "args": args, "rc": proc.returncode,
            "tail": tail, "seconds": round(time.time() - start, 1)}


def main() -> int:
    # Windows consoles are often GBK; subprocess output can contain replacement chars.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", metavar="LABEL", default=None,
                    help="also build dist/mcbridge-launcher-<LABEL>.zip")
    ap.add_argument("--json", default=None)
    ap.add_argument("--accept", action="store_true",
                    help="after --build, run the clean-host acceptance on that zip (p208)")
    args = ap.parse_args()

    env_note = []
    if "JAVA_HOME" not in os.environ:
        jdk = ROOT.parent / ".toolchain" / "jdk"
        if jdk.is_dir():
            os.environ["JAVA_HOME"] = str(jdk)
            env_note.append(f"JAVA_HOME={jdk}")
    if "GRADLE_USER_HOME" not in os.environ:
        gh = ROOT / ".toolchain" / "gradle-home"
        if gh.is_dir():
            os.environ["GRADLE_USER_HOME"] = str(gh)
            env_note.append(f"GRADLE_USER_HOME={gh}")

    steps = [
        ("hash manifest matches the tree", [PY, "tools/check_hashes.py"]),
        ("every run README/result is hashed", [PY, "tools/check_manifest_coverage.py"]),
        ("evidence gate (suite + unit tests + encoding)", [PY, "tools/verify_evidence.py"]),
    ]
    zip_path = None
    if args.build:
        steps.append((f"portable build {args.build}",
                      [PY, "tools/build_portable.py", "--label", args.build]))
        zip_path = ROOT / "dist" / f"mcbridge-launcher-{args.build}.zip"
        if args.accept:
            steps.append((f"clean-host acceptance {zip_path.name}",
                          [PY, "runs/p208-cross-platform/run_clean_host.py",
                           "--zip", str(zip_path), "--out", "release-accept.json"]))

    results = []
    ok = True
    for name, cmd in steps:
        print(f"== {name}", flush=True)
        r = run(name, cmd)
        results.append(r)
        print("   rc", r["rc"], "|", " / ".join(r["tail"])[:200], flush=True)
        if r["rc"] != 0:
            ok = False
            break

    if args.build and ok:
        if zip_path.is_file():
            print(f"   zip {zip_path.name} {zip_path.stat().st_size} bytes")
        else:
            ok = False
            print("   zip missing after build")

    payload = {"passed": ok, "env": env_note, "steps": results,
               "zip": str(zip_path) if zip_path else None,
               "zip_bytes": zip_path.stat().st_size if zip_path and zip_path.is_file() else None}
    if args.json:
        Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nrelease_check:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
