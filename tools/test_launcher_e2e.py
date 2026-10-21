#!/usr/bin/env python3
"""End-to-end launcher regression: install (optional) -> launch -> wait for the main menu -> exit.

Example:

    python tools/test_launcher_e2e.py --root work/launcher-e2e --mc 1.21.1
    python tools/test_launcher_e2e.py --root work/launcher-fresh2 --no-install

Exit 0 when the client reached the main menu (log has "Setting user" and "Backend library"),
1 when it did not, 2 on setup errors.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402


def find_installed(root: Path, mc: str) -> str | None:
    for d in sorted((root / "versions").glob(f"fabric-loader-*-{mc}")):
        if (d / f"{d.name}.json").exists():
            return d.name
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT / "work" / "launcher-e2e"))
    ap.add_argument("--mc", default="1.21.1")
    ap.add_argument("--username", default="E2EUser")
    ap.add_argument("--no-install", action="store_true")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    try:
        if args.no_install:
            vid = find_installed(root, args.mc)
            if not vid:
                print(f"no fabric version for {args.mc} under {root}; drop --no-install")
                return 2
        else:
            mclaunch.install_vanilla_launcher_profile(args.mc, root)
            vid = mclaunch.install_fabric(args.mc, root)
    except Exception as exc:  # noqa: BLE001
        print("install failed:", exc)
        return 2

    cmd, log, _ = mclaunch.build_command(vid, root, args.username, "2G")
    log.parent.mkdir(parents=True, exist_ok=True)
    print("launching", vid, "->", log)
    with open(log, "w", encoding="utf-8", errors="replace") as out:
        out.write(" ".join(cmd) + "\n")
        out.flush()
        proc = subprocess.Popen(cmd, cwd=str(root), stdout=out, stderr=subprocess.STDOUT)
        deadline = time.time() + args.timeout
        ok = False
        try:
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
                if f"Setting user: {args.username}" in text and "Backend library" in text:
                    ok = True
                    break
                time.sleep(1)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    for bad in ("AccessDenied", "Uncaught exception in thread"):
        if bad in text:
            print("failed marker:", bad)
            ok = False
    print("RESULT:", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
