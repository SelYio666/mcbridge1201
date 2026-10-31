#!/usr/bin/env python3
"""Run the shipped portable package the way a recipient's machine would.

The point is the environment, not the launcher: tools/test_portable.py does
`dict(os.environ, ...)`, so it inherits whatever the authoring shell had -
PYTHONHOME, a JDK on PATH, an existing .minecraft. That can only ever confirm
"it works on the machine that built it".

This harness builds a scrubbed environment instead:

  PATH            only C:\\Windows\\System32 and C:\\Windows (no Python, no JDK)
  PYTHON*         removed
  JAVA_HOME/MC_JAVA removed
  HOME/USERPROFILE/TEMP/APPDATA/LOCALAPPDATA
                  point at fresh empty directories, so no user profile,
                  no installed runtime and no existing .minecraft is visible

and then measures, in that environment: whether a system python is reachable at
all (the scrub has to be proven, otherwise the rest is meaningless), which
interpreter the package actually uses, whether /api/status and /guide answer,
whether a leaked PYTHONHOME/PYTHONPATH changes anything, and whether the package
carries any .jar.

Boundary: this is a scrubbed environment on the machine that built the package,
not a different computer. Windows itself, the JDK used for the game and the
network are still this host's.

Usage: python runs/p208-cross-platform/run_clean_host.py [--keep]
Exit codes: 0 all checks pass, 1 a check failed.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUN = ROOT / "runs" / "p208-cross-platform"
WORK = ROOT / "work" / "tmp" / "p208-clean-host"
PORT = 8811


def scrubbed(home: Path, tmp: Path) -> dict:
    """An environment with no Python, no JDK and an empty user profile."""
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    env = {
        "SystemRoot": str(Path(os.environ.get("SystemRoot", r"C:\Windows"))),
        "SystemDrive": os.environ.get("SystemDrive", "C:"),
        "windir": str(Path(os.environ.get("SystemRoot", r"C:\Windows"))),
        "PATH": f"{system32};{Path(os.environ.get('SystemRoot', r'C:\\Windows'))}",
        "COMSPEC": str(system32 / "cmd.exe"),
        "TEMP": str(tmp),
        "TMP": str(tmp),
        "HOME": str(home),
        "USERPROFILE": str(home),
        "APPDATA": str(home / "AppData" / "Roaming"),
        "LOCALAPPDATA": str(home / "AppData" / "Local"),
        "USERNAME": "p208",
        "LANG": "en_US.UTF-8",
    }
    for sub in ("AppData/Roaming", "AppData/Local"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    return env


def which_under(env: dict, name: str) -> str | None:
    """Resolve `name` using the scrubbed PATH, evaluated by the host interpreter."""
    code = f"import shutil; print(shutil.which({name!r}) or 'NONE')"
    out = subprocess.run([sys.executable, "-c", code], env=env,
                         capture_output=True, text=True, timeout=60).stdout.strip()
    return None if out == "NONE" else out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="keep the extracted tree")
    ap.add_argument("--overlay-launcher", action="store_true",
                    help="replace the package's launcher/*.py with the current worktree")
    ap.add_argument("--out", default="clean-host.json")
    args = ap.parse_args()

    packages = list((ROOT / "dist").glob("mcbridge-launcher-*.zip"))
    if not packages:
        print("SKIP: no dist/mcbridge-launcher-*.zip")
        return 2
    # natural version order: "0.5.10" must beat "0.5.7" (plain string sort puts it first)
    import re as _re
    packages.sort(key=lambda p: [int(x) for x in _re.findall(r"\d+", p.stem)])
    package = packages[-1]

    if WORK.exists():
        shutil.rmtree(WORK)
    home, tmp, pkg_dir = WORK / "home", WORK / "tmp", WORK / "pkg"
    for d in (home, tmp, pkg_dir):
        d.mkdir(parents=True)
    with zipfile.ZipFile(package) as z:
        names = z.namelist()
        z.extractall(pkg_dir)
    tops = [p for p in pkg_dir.iterdir() if p.is_dir()]
    pkg = tops[0] if len(tops) == 1 else pkg_dir

    overlaid = []
    if args.overlay_launcher:
        # The zip's vendored dependencies are the ones we cannot rebuild here
        # (minecraft-launcher-lib is not installed on this machine), but the
        # code under test is the current worktree, so swap only the sources.
        for src in sorted((ROOT / "launcher").glob("*.py")):
            dst = pkg / "launcher" / src.name
            if dst.exists():
                shutil.copy2(src, dst)
                overlaid.append(src.name)

    env = scrubbed(home, tmp)
    checks: dict[str, bool] = {}
    detail: dict[str, object] = {}

    # 1. The scrub itself. If this is not empty, every later check is vacuous.
    py_on_path = which_under(env, "python")
    java_on_path = which_under(env, "java")
    checks["no_system_python"] = py_on_path is None
    checks["no_system_java"] = java_on_path is None
    detail["path_lookup"] = {"python": py_on_path, "java": java_on_path, "PATH": env["PATH"]}

    # 2. What the package actually ships and starts.
    py = pkg / "python" / "python.exe"
    checks["bundled_python"] = py.exists()
    launchers = sorted(p.name for p in pkg.iterdir()
                       if p.suffix.lower() in (".bat", ".cmd", ".sh", ".command", ".ps1"))
    jars = [n for n in names if n.lower().endswith(".jar")]
    checks["no_jars_shipped"] = not jars
    detail["package"] = {"zip": package.name, "bytes": package.stat().st_size,
                         "entries": len(names), "launchers": launchers, "jars": jars}

    if py.exists():
        # The repo path contains Chinese; the embedded interpreter would write
        # cp936 to a pipe, so force its stdio to UTF-8 instead of guessing.
        r = subprocess.run([str(py), "-X", "utf8", "-c",
                            "import sys;print(sys.prefix);print(sys.executable)"],
                           env=env, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
        lines = (r.stdout or "").strip().splitlines()
        prefix = lines[0] if lines else ""
        checks["interpreter_is_bundled"] = (
            Path(prefix).is_absolute() and Path(prefix).resolve().is_relative_to(pkg.resolve()))
        detail["interpreter"] = {"rc": r.returncode, "prefix": prefix,
                                 "executable": lines[1] if len(lines) > 1 else "",
                                 "stderr": (r.stderr or "").strip()[-200:]}

        # 3. A leaked PYTHONHOME/PYTHONPATH must not reach the embedded runtime.
        hostile = dict(env, PYTHONHOME=str(WORK / "nope-home"),
                       PYTHONPATH=str(WORK / "nope-path"))
        r2 = subprocess.run([str(py), "-X", "utf8", "-c", "import sys;print(sys.prefix)"],
                            env=hostile, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=120)
        hostile_prefix = (r2.stdout or "").strip()
        checks["hostile_pythonhome_ignored"] = r2.returncode == 0 and hostile_prefix == prefix
        detail["hostile_env"] = {"rc": r2.returncode, "prefix": hostile_prefix,
                                 "stderr": (r2.stderr or "").strip()[-200:]}

        # 4. The launcher answers, in the scrubbed environment.
        run_env = dict(env, LAUNCHER_PORT=str(PORT), LAUNCHER_OPEN="0")
        proc = subprocess.Popen([str(py), str(pkg / "bootstrap.py")], cwd=str(pkg), env=run_env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        base = f"http://127.0.0.1:{PORT}"
        status_ok = guide_ok = False
        payload = {}
        try:
            deadline = time.time() + 45
            while time.time() < deadline and not status_ok:
                try:
                    with urllib.request.urlopen(base + "/api/status", timeout=5) as resp:
                        payload = json.loads(resp.read())
                        status_ok = resp.status == 200 and "versions" in payload
                except Exception:  # noqa: BLE001 - retry until the deadline
                    time.sleep(0.5)
            for _ in range(10):
                try:
                    with urllib.request.urlopen(base + "/guide", timeout=10) as resp:
                        guide_ok = resp.status == 200 and "使用说明" in resp.read().decode("utf-8")
                    break
                except Exception:  # noqa: BLE001
                    time.sleep(0.5)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        checks["api_status"] = status_ok
        checks["guide_page"] = guide_ok
        detail["status"] = {"ok": status_ok, "keys": sorted(payload),
                            "root": payload.get("root"),
                            "versions": len(payload.get("versions") or []),
                            "java": payload.get("java"),
                            "java_error": payload.get("java_error")}

    result = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "package": str(package.relative_to(ROOT)),
        "launcher_sources": ("current worktree over " + package.name) if overlaid
                            else f"as shipped in {package.name}",
        "overlaid": overlaid,
        "scrub": {"PATH": env["PATH"], "home": str(home), "temp": str(tmp)},
        "checks": checks,
        "passed": sum(1 for v in checks.values() if v),
        "total": len(checks),
        "detail": detail,
        "boundary": ["same machine, different environment - not a different computer",
                     "Windows and the network are still this host's"],
    }
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'} {name}")
    print(f"{result['passed']}/{result['total']} -> runs/p208-cross-platform/{args.out}"
          f"  (sources: {result['launcher_sources']})")
    print("interpreter:", detail.get("interpreter", {}).get("prefix"))
    print("api root:", detail.get("status", {}).get("root"))

    if not args.keep:
        shutil.rmtree(WORK, ignore_errors=True)
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
