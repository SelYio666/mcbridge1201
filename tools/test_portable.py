#!/usr/bin/env python3
"""Smoke-test a built portable package (dist/mcbridge-launcher-*.zip).

Checks, without touching any game files:
  1. the bundled python + vendored deps import (minecraft_launcher_lib available);
  2. the packaged launcher core verifies an already-installed version (if given);
  3. the packaged server answers /api/status and /guide.

Usage:
  python tools/test_portable.py --root work/launcher-e2e --version neoforge-21.1.264
Exit codes: 0 ok, 1 failed, 2 no package to test.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def latest_package() -> Path | None:
    cands = sorted((ROOT / "dist").glob("mcbridge-launcher-*.zip"))
    return cands[-1] if cands else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", default="", help="package to test (default: newest dist/*.zip)")
    ap.add_argument("--root", default=str(ROOT / "work" / "launcher-e2e"),
                    help="existing game root used for the verify check")
    ap.add_argument("--version", default="neoforge-21.1.264", help="installed version to verify")
    ap.add_argument("--port", type=int, default=8799)
    args = ap.parse_args()

    zip_path = Path(args.zip) if args.zip else latest_package()
    if not zip_path or not zip_path.exists():
        print("SKIP: no dist/mcbridge-launcher-*.zip; run tools/build_portable.py first")
        return 2
    print("package:", zip_path, zip_path.stat().st_size, "bytes")

    test_dir = ROOT / "work" / "portable-test"
    if test_dir.exists():
        shutil.rmtree(test_dir)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(test_dir)
    tops = [p for p in test_dir.iterdir() if p.is_dir()]
    pkg = tops[0] if tops else test_dir
    py = pkg / "python" / "python.exe"
    if not py.exists():
        print("FAIL: package has no bundled python (built with --no-python?)")
        return 1

    launcher = pkg / "launcher"
    code = ("import sys; sys.path.insert(0, r'%s'); "
            "import minecraft_launcher_lib, requests, certifi, urllib3; "
            "import backend; print('mll available:', backend.AVAILABLE)") % launcher
    r = subprocess.run([str(py), "-c", code], capture_output=True, text=True, timeout=120)
    deps_ok = r.returncode == 0 and "mll available: True" in (r.stdout or "")
    print("deps:", deps_ok, (r.stderr or "").strip()[-200:])

    ver_ok = True
    if args.version and (ROOT / args.root).exists():
        r = subprocess.run([str(py), str(launcher / "mclaunch.py"), "verify",
                            args.version, args.root],
                           capture_output=True, text=True, timeout=120)
        last = (r.stdout or "").strip().splitlines()[-1] if (r.stdout or "").strip() else ""
        ver_ok = r.returncode == 0 and "RESULT: OK" in (r.stdout or "")
        print("verify:", ver_ok, last)

    env = dict(os.environ, LAUNCHER_OPEN="0", LAUNCHER_PORT=str(args.port))
    proc = subprocess.Popen([str(py), str(pkg / "bootstrap.py")], cwd=str(pkg), env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok_status = ok_guide = False
    base = f"http://127.0.0.1:{args.port}"
    try:
        deadline = time.time() + 30
        while time.time() < deadline and not ok_status:
            try:
                with urllib.request.urlopen(base + "/api/status", timeout=5) as resp:
                    ok_status = resp.status == 200 and "versions" in json.loads(resp.read())
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        for _ in range(10):
            try:
                with urllib.request.urlopen(base + "/guide", timeout=10) as resp:
                    ok_guide = resp.status == 200 and "使用说明" in resp.read().decode("utf-8")
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    print("server /api/status:", ok_status, " /guide:", ok_guide)
    ok = deps_ok and ver_ok and ok_status and ok_guide
    print("RESULT:", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
