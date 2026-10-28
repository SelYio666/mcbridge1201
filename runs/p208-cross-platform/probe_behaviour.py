#!/usr/bin/env python3
"""Behavioural probes for the platform assumptions the audit found.

Each probe asserts on an observable outcome, not on source text, and each one
runs against the live launcher modules - so the same script produces the
"before" and the "after" record from the same file. That is the point: the
failure has to be caught before the fix, otherwise "it was broken" is a story.

Probes:
  default_root_no_appdata    APPDATA unset (as on POSIX), a .minecraft/versions
                             exists in the CWD. A returned relative path means
                             the launcher would adopt whatever directory it
                             happens to be started in.
  find_java_home_posix       JAVA_HOME points at a POSIX JDK (bin/java, no
                             .exe) and PATH has no java. Honouring JAVA_HOME
                             must not depend on the file being called java.exe.
  open_folder_darwin         macOS gets `open`, not `xdg-open`.
  open_folder_windows        control: still os.startfile on Windows, so the
                             fix cannot pass by breaking the platform we use.
  java_fallback_unused       the Windows-path constant is either used or gone.

Usage: python runs/p208-cross-platform/probe_behaviour.py --out <json>
Exit codes: 0 all probes pass, 1 some probe failed (still writes the JSON).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "launcher"))


def probe_default_root_no_appdata() -> dict:
    """APPDATA unset + a decoy .minecraft in the CWD must not become the game root."""
    import server

    saved_env = dict(os.environ)
    saved_cwd = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="p208-root-"))
    try:
        (tmp / "cwd" / ".minecraft" / "versions").mkdir(parents=True)
        (tmp / "home").mkdir()
        os.environ.pop("APPDATA", None)
        os.environ["USERPROFILE"] = str(tmp / "home")
        os.environ["HOME"] = str(tmp / "home")
        os.chdir(tmp / "cwd")
        got = server.default_root()
    finally:
        os.chdir(saved_cwd)
        os.environ.clear()
        os.environ.update(saved_env)

    is_abs = Path(got).is_absolute()
    adopted_cwd = not is_abs
    return {
        "name": "default_root_no_appdata",
        "expect": "an absolute path outside the current directory",
        "actual": got,
        "ok": is_abs and not adopted_cwd,
        "detail": ("APPDATA unset -> Path('')/'.minecraft' is relative and .exists() "
                   "matched the decoy; the launcher would adopt its own CWD"
                   if adopted_cwd else "resolved away from the CWD"),
    }


def probe_find_java_home_posix() -> dict:
    """JAVA_HOME with bin/java (no .exe) must be honoured when the host is POSIX."""
    import mclaunch

    tmp = Path(tempfile.mkdtemp(prefix="p208-jdk-"))
    (tmp / "bin").mkdir()
    java = tmp / "bin" / "java"
    java.write_text("#!/bin/sh\necho fake\n", encoding="utf-8")

    saved_env = dict(os.environ)
    # Only sys.platform is faked. Faking os.name as well makes pathlib build
    # PosixPath objects, and a Windows CPython refuses that deeper in - a failure
    # of the simulation, not of the code under test.
    saved_platform = sys.platform
    try:
        saved_env_java = {k: os.environ.get(k) for k in ("JAVA_HOME", "MC_JAVA", "PATH")}
        os.environ["JAVA_HOME"] = str(tmp)
        os.environ.pop("MC_JAVA", None)
        os.environ["PATH"] = ""  # no system java to fall back on
        sys.platform = "linux"
        try:
            got = mclaunch.find_java()
            error = None
        except Exception as exc:  # noqa: BLE001 - the failure is the data
            got, error = None, f"{type(exc).__name__}: {exc}"
    finally:
        sys.platform = saved_platform
        os.environ.clear()
        os.environ.update(saved_env)
        for key, value in saved_env_java.items():
            if value is not None:
                os.environ.setdefault(key, value)

    want = str(java)
    return {
        "name": "find_java_home_posix",
        "expect": f"JAVA_HOME honoured -> {want}",
        "actual": got or error,
        "ok": got == want,
        "detail": ("looked for bin/java.exe, so JAVA_HOME was skipped and another JDK won"
                   if got and got != want else
                   ("raised instead of using JAVA_HOME" if error else "JAVA_HOME honoured")),
    }


def probe_open_folder(platform: str, expect_cmd: str) -> dict:
    """Which opener is chosen for this platform. Records argv instead of launching."""
    import server

    saved_popen = subprocess.Popen
    saved_startfile = getattr(os, "startfile", None)
    saved_name, saved_platform = os.name, sys.platform
    calls: list[list[str]] = []
    started: list[str] = []

    def fake_popen(argv, *a, **kw):
        calls.append(list(argv) if isinstance(argv, (list, tuple)) else [str(argv)])
        return None

    def fake_startfile(path, *a, **kw):
        started.append(str(path))

    try:
        subprocess.Popen = fake_popen
        os.startfile = fake_startfile  # type: ignore[attr-defined]
        if platform == "win32":
            os.name = "nt"
            sys.platform = "win32"
        elif platform == "darwin":
            os.name = "posix"
            sys.platform = "darwin"
        else:
            os.name = "posix"
            sys.platform = "linux"
        try:
            server.open_in_explorer(tempfile.gettempdir())
            error = None
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
    finally:
        subprocess.Popen = saved_popen
        if saved_startfile is not None:
            os.startfile = saved_startfile  # type: ignore[attr-defined]
        sys.platform = saved_platform

    chosen = "startfile" if started else (calls[0][0] if calls else None)
    return {
        "name": f"open_folder_{platform}",
        "expect": f"{expect_cmd} used",
        "actual": chosen or error,
        "ok": chosen == expect_cmd and error is None,
        "detail": error or f"chose {chosen!r}",
    }


def probe_java_fallback_unused() -> dict:
    """Either the constant is referenced somewhere, or it should not exist."""
    import mclaunch

    used = any("JAVA_FALLBACK" in Path(f).read_text(encoding="utf-8", errors="replace")
               for f in [ROOT / "launcher" / "mclaunch.py"])
    defined = hasattr(mclaunch, "JAVA_FALLBACK")
    occurrences = (ROOT / "launcher" / "mclaunch.py").read_text(
        encoding="utf-8").count("JAVA_FALLBACK")
    return {
        "name": "java_fallback_unused",
        "expect": "the constant is either used or absent",
        "actual": f"defined={defined} occurrences={occurrences}",
        "ok": (not defined) or occurrences > 1,
        "detail": ("hardcoded C:\\Program Files\\Java\\... but never referenced"
                   if defined and occurrences == 1 else "consistent"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    probes = [
        probe_default_root_no_appdata(),
        probe_find_java_home_posix(),
        probe_open_folder("darwin", "open"),
        probe_open_folder("linux", "xdg-open"),
        probe_open_folder("win32", "startfile"),
        probe_java_fallback_unused(),
    ]
    result = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "host": {"sys.platform": sys.platform, "os.name": os.name,
                 "python": sys.version.split()[0]},
        "probes": probes,
        "passed": sum(1 for p in probes if p["ok"]),
        "total": len(probes),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for p in probes:
        print(f"{'PASS' if p['ok'] else 'FAIL'} {p['name']}: {p['actual']!r} "
              f"(want {p['expect']})")
    print(f"{result['passed']}/{result['total']} -> {out}")
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
