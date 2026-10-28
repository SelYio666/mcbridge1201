#!/usr/bin/env python3
"""Audit how much of the delivery path is Windows-only, without a second machine.

Two independent passes, because either one alone is easy to fool:

  static   every tracked *.py is scanned for constructs that change meaning on
           POSIX (os.name / sys.platform branches, winreg, msvcrt, .exe
           binaries, drive letters, %APPDATA% style env vars, os.startfile,
           chcp, taskkill). Hits are classified as delivery (what a recipient
           runs) or harness (authoring-only evidence tooling).

  dynamic  each delivery module is imported in a fresh subprocess where
           sys.platform is "linux" and os.name is "posix", with Windows-only
           stdlib modules made unimportable. An ImportError there is a module
           that cannot even load on Linux.

This is an audit, not a Linux run: no POSIX kernel is involved, so it proves
which Windows-only dependencies exist and which modules survive the import, and
nothing about runtime behaviour on a real POSIX host. The README says so too.

Usage:
  python tools/audit_portability.py [--out runs/p208-cross-platform/audit.json]
Exit codes: 0 audit produced (findings are data, not failure), 1 audit error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Code a recipient actually runs: the launcher itself plus the two scripts that
# build and smoke-test the portable package. Everything else in tools/, runs/
# and probes/ is authoring machinery and is reported separately.
DELIVERY_DIRS = ("launcher",)
DELIVERY_FILES = (
    "tools/build_portable.py",
    "tools/test_portable.py",
)

# Modules that only exist on Windows. Blocking them is how the dynamic pass
# turns "this would fail on Linux" into an ImportError we can observe.
WINDOWS_ONLY = ("winreg", "msvcrt", "_winapi", "_msi", "winsound", "win32api",
                "win32con", "win32com", "pywintypes", "ntsecuritycon")

# (name, regex, why it matters on POSIX)
PATTERNS = [
    ("os.name-branch", re.compile(r"os\.name\s*=="), "behaviour silently takes the non-nt branch"),
    ("sys.platform-branch", re.compile(r"sys\.platform\s*(==|in)"), "same, keyed on platform string"),
    ("winreg", re.compile(r"\bwinreg\b"), "module does not exist on POSIX"),
    ("msvcrt", re.compile(r"\bmsvcrt\b"), "module does not exist on POSIX"),
    ("ctypes.windll", re.compile(r"ctypes\.windll|\bwindll\b"), "Win32 API only"),
    ("os.startfile", re.compile(r"os\.startfile"), "Windows-only; needs open/xdg-open"),
    ("xdg-open", re.compile(r"xdg-open"), "absent on macOS, needs open"),
    ("taskkill", re.compile(r"\btaskkill\b"), "process control is Windows-only"),
    ("chcp", re.compile(r"\bchcp\b"), "console code page is Windows-only"),
    ("java.exe", re.compile(r"java\.exe"), "the binary is called java on POSIX"),
    ("python.exe", re.compile(r"python\.exe"), "same for the interpreter"),
    # "C:////Program" / "D:/mc" but not the "s:/" inside "https://"
    ("drive-letter", re.compile(r"[A-Za-z]:[\\\\/][A-Za-z\u4e00-\u9fff]"), "absolute Windows path"),
    ("backslash-path", re.compile(r"Path\(r\"[^\"]*\\\\"), "backslash separators"),
    # %APPDATA% yes, strftime's %Y%m%d is not an env var
    ("percent-env", re.compile(r"%[A-Z][A-Z0-9_]{2,}%"), "cmd.exe variable syntax"),
    ("appdata", re.compile(r"APPDATA|LOCALAPPDATA|ProgramData|Program Files"),
     "Windows env vars / install roots"),
    ("gbk", re.compile(r"encoding=[\"']gbk|encoding=[\"']cp936"), "locale codepage, not portable"),
    ("shell-cmd", re.compile(r"shell\s*=\s*True"), "quoting differs per shell"),
]

DRIVER = r'''
import sys, os
# Import the Windows-flavoured stdlib first: flipping sys.platform and then
# importing subprocess would make it try _posixsubprocess, which does not exist
# in a Windows CPython - a false positive that says nothing about our code.
import subprocess, json, shutil, zipfile, threading, time, http.server, webbrowser
sys.platform = "linux"
# os.name is deliberately NOT flipped. pathlib reads it at import time and a
# Windows CPython refuses to instantiate PosixPath ("cannot instantiate
# 'PosixPath' on your system"), so that would manufacture a failure that says
# nothing about this code. The import graph is what this pass can honestly test.
BLOCK = set(json.loads(sys.argv[2]))
class Blocker:
    """Refuse Windows-only modules, so a dependency surfaces as an ImportError."""
    def find_spec(self, name, path=None, target=None):
        root = name.split(".")[0]
        if root in BLOCK and name not in sys.modules:
            raise ImportError("blocked-windows-only:" + name)
        return None
sys.meta_path.insert(0, Blocker())
sys.path.insert(0, sys.argv[1])
try:
    __import__(sys.argv[3])
except BaseException as exc:
    print("AUDIT_ERR " + type(exc).__name__ + ": " + str(exc).replace("\n", " "))
    raise SystemExit(3)
print("AUDIT_OK " + sys.argv[3])
'''


def tracked_py() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z", "*.py"], cwd=ROOT,
                         capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def classify(path: str) -> str:
    if path in DELIVERY_FILES or path.split("/")[0] in DELIVERY_DIRS:
        return "delivery"
    return "harness"


GUARD = re.compile(r"platform\.startswith\(|os\.name\s*==|sys\.platform\s*(==|in)"
                  r"|is_windows|startswith\(\"win\"\)")


def scan(path: Path) -> list[dict]:
    """Pattern hits, annotated with whether the platform detail is handled.

    A hit on its own says nothing: `os.startfile` inside `if platform.startswith
    ("win")` is correct code. Each hit therefore carries
      guard        the nearest platform check within the 20 lines above it, if any
      in_docstring line sits between an odd number of triple quotes
    so the summary can separate "handled" from "bare" instead of reporting one
    misleading total.
    """
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        lineno = idx + 1
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Odd count of """ before this line means we are inside a docstring.
        in_doc = (text.count(chr(34) * 3, 0, sum(len(x) + 1 for x in lines[:idx])) % 2) == 1
        if stripped.startswith(chr(34) * 3):  # a one-line docstring counts too
            in_doc = True
        # The guard may be on the line itself: `if os.name == "nt":`, or the
        # ternary that picks the executable name.
        guard = None
        if GUARD.search(line):
            guard = stripped[:100]
        for back in range(max(0, idx - 20), idx):
            if GUARD.search(lines[back]):
                guard = lines[back].strip()[:100]
        for name, rx, why in PATTERNS:
            if rx.search(line):
                hits.append({"line": lineno, "pattern": name, "why": why,
                             "code": stripped[:120], "guard": guard,
                             "in_docstring": in_doc,
                             "handled": in_doc or guard is not None})
    return hits


def module_name(path: str) -> str | None:
    """Import name for a delivery file, assuming its own directory is on sys.path."""
    p = Path(path)
    if p.parent.name != "launcher":
        return None
    return p.stem


def dynamic(modules: list[tuple[str, str]]) -> list[dict]:
    out = []
    launcher = ROOT / "launcher"
    for path, mod in modules:
        started = time.time()
        proc = subprocess.run(
            [sys.executable, "-c", DRIVER, str(launcher), json.dumps(list(WINDOWS_ONLY)), mod],
            cwd=str(ROOT), capture_output=True, text=True, timeout=120,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        stdout = (proc.stdout or "").strip()
        ok = proc.returncode == 0 and stdout.startswith("AUDIT_OK")
        out.append({
            "path": path,
            "module": mod,
            "ok": ok,
            "rc": proc.returncode,
            "stdout": stdout.splitlines()[-1] if stdout else "",
            "stderr": (proc.stderr or "").strip().splitlines()[-1:] or [],
            "seconds": round(time.time() - started, 2),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "runs" / "p208-cross-platform" / "audit.json"))
    args = ap.parse_args()

    files = tracked_py()
    rows = []
    for rel in files:
        hits = scan(ROOT / rel)
        if hits:
            rows.append({"path": rel, "kind": classify(rel), "hits": hits})

    modules = [(rel, m) for rel in files
               if classify(rel) == "delivery" and (m := module_name(rel))]
    modules.sort()
    dyn = dynamic(modules)

    delivery_hits = sum(len(r["hits"]) for r in rows if r["kind"] == "delivery")
    docstring_hits = sum(1 for r in rows if r["kind"] == "delivery"
                         for h in r["hits"] if h["in_docstring"])
    bare_hits = sum(1 for r in rows if r["kind"] == "delivery"
                    for h in r["hits"] if not h["handled"])
    guarded_hits = delivery_hits - docstring_hits - bare_hits
    harness_hits = sum(len(r["hits"]) for r in rows if r["kind"] == "harness")
    by_pattern: dict[str, int] = {}
    for row in rows:
        if row["kind"] != "delivery":
            continue
        for hit in row["hits"]:
            by_pattern[hit["pattern"]] = by_pattern.get(hit["pattern"], 0) + 1

    result = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "host": {"sys.platform": sys.platform, "os.name": os.name,
                 "python": sys.version.split()[0]},
        "simulation": {"sys.platform": "linux", "os.name": os.name,
                       "blocked_modules": list(WINDOWS_ONLY)},
        "caveats": [
            "No POSIX kernel is involved: this is an import-level audit on Windows.",
            "The dynamic pass flips sys.platform in a subprocess and blocks Windows-only "
            "modules; os.name is left alone because a Windows CPython cannot instantiate "
            "PosixPath, which would manufacture a failure instead of measuring one.",
            "It therefore proves the import graph only: it cannot observe path semantics "
            "(separators, case sensitivity, locking, signals) that need a real POSIX host.",
            "Harness hits are authoring tooling (runs/, probes/); they are counted but not "
            "treated as delivery defects.",
        ],
        "counts": {
            "tracked_py": len(files),
            "delivery_files_with_hits": sum(1 for r in rows if r["kind"] == "delivery"),
            "delivery_hits": delivery_hits,
            "harness_hits": harness_hits,
            "delivery_hits_docstring": docstring_hits,
            "delivery_hits_guarded": guarded_hits,
            "delivery_hits_bare": bare_hits,
            "delivery_modules_imported": len(dyn),
            "delivery_modules_ok": sum(1 for d in dyn if d["ok"]),
        },
        "delivery_hits_by_pattern": dict(sorted(by_pattern.items())),
        "delivery_hits_by_state": {
            "docstring": docstring_hits,
            "guarded": guarded_hits,
            "bare": bare_hits,
        },
        "static": rows,
        "dynamic": dyn,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"tracked *.py: {len(files)}")
    print(f"delivery hits: {delivery_hits} in {result['counts']['delivery_files_with_hits']} files "
          f"(docstring {docstring_hits}, guarded {guarded_hits}, bare {bare_hits}) "
          f"| harness hits: {harness_hits}")
    print(f"delivery modules imported under posix simulation: "
          f"{result['counts']['delivery_modules_ok']}/{len(dyn)}")
    for d in dyn:
        print(("  OK   " if d["ok"] else "  FAIL ") + d["module"] + " " + d["stdout"])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
