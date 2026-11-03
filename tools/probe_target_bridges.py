#!/usr/bin/env python3
"""Probe whether the current bridge sources compile for a target profile, and record why not.

This is the measurement behind runs/p251: after the library closure is pinned, how far do the
existing bridges get for 1.21.4? It records the error count and samples, and separates the two
kinds of failure that look the same in a compiler log:

* a **missing third-party mod API** (Balm and friends) - the dependency is not part of the game
  closure, so this is not evidence about the conversion;
* a **real API difference** in the target - the bridge's Java no longer matches.

    python tools/probe_target_bridges.py
    python tools/probe_target_bridges.py --profile targets/fabric-1.21.4.json --out runs/pNNN-x

Exit codes: 0 probe ran (regardless of compile result), 2 a required input is missing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE = ROOT / "targets" / "fabric-1.21.4.json"
DEFAULT_OUT = ROOT / "runs" / "p251-1214-compile-closure"

# Package roots that belong to mods, not to the game. An error naming one of these is a missing
# mod dependency, not a target API change.
MOD_PACKAGES = ("net/blay09/", "net/blay09.mods", "dev/architectury", "com/teamresourceful",
                "net/fabricmc/fabric/api", "io/wispforest")


def java_home() -> str | None:
    env = os.environ.get("JAVA_HOME")
    if env and (Path(env) / "bin" / "java.exe").exists():
        return env
    for cand in (ROOT.parent / ".toolchain" / "jdk", ROOT / ".toolchain" / "jdk"):
        if (cand / "bin" / "java.exe").exists():
            os.environ["JAVA_HOME"] = str(cand)
            return str(cand)
    return None


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default=str(DEFAULT_PROFILE))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--closure-total", type=int, default=None,
                    help="jar count of the closure BEFORE the fabric-api modules were expanded,"
                         " so the delta can be reported")
    args = ap.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    profile_path = Path(args.profile)
    if not profile_path.is_file():
        print(f"missing profile: {profile_path}", file=sys.stderr)
        return 2
    if java_home() is None:
        print("need a JDK (JAVA_HOME)", file=sys.stderr)
        return 2

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    closure = (profile.get("indices") or {}).get("libClosure") or {}
    closure_path = ROOT / closure["path"] if closure.get("path") else None
    closure_stats = {}
    if closure_path and closure_path.is_file():
        lock = json.loads(closure_path.read_text(encoding="utf-8"))
        modules = [e for e in lock["libraries"] if e.get("role", "").startswith("fabric api module")]
        closure_stats = {
            "lock": closure["path"],
            "jars": lock["count"],
            "modules": len(modules),
            "gameJars": lock["count"] - len(modules),
            "totalBytes": lock["totalBytes"],
            "skipped": len(lock.get("skipped") or []),
        }

    target = (out / "bridges").resolve()
    probe = subprocess.run([sys.executable, str(ROOT / "tools" / "build_bridges.py"),
                            "--profile", str(profile_path), "--out", str(target)],
                           cwd=ROOT, capture_output=True, text=True, errors="replace")
    log = (probe.stdout or "") + (probe.stderr or "")
    (out / "build-bridges.log").write_text(log, encoding="utf-8", newline="\n")

    lines = [l.rstrip() for l in log.splitlines()]
    err_lines = [l for l in lines if ("错误:" in l or ": error:" in l)]
    by_file: dict[str, int] = {}
    for l in err_lines:
        m = re.search(r"bridge[\\/](\w+\.java):(\d+)", l)
        if m:
            by_file[m.group(1)] = by_file.get(m.group(1), 0) + 1
    mod_related = [f for f in by_file if any(p in f for p in ("Balm", "Architectury"))]
    other = [f for f in by_file if f not in mod_related]
    produced = len(list(target.rglob("*.class"))) if target.is_dir() else 0

    result = {
        "workstream": "B03 infrastructure: 1.21.4 compile closure and bridge probe",
        "profile": profile_path.relative_to(ROOT).as_posix(),
        "closure": closure_stats,
        "probe": {
            "rc": probe.returncode,
            "compileErrors": len(err_lines),
            "classesProduced": produced,
            "errorsByFile": dict(sorted(by_file.items(), key=lambda kv: -kv[1])),
            "modApiSmell": mod_related,
            "otherFiles": other,
            "beforeModules": args.closure_total,
            "sample": err_lines[:6],
        },
        "reading": {
            "modApi": "errors naming Balm/Architectury-style packages mean the *mod* dependency is"
                      " absent from the game closure; that is not evidence about the conversion",
            "apiChange": "the rest are real mismatches between the bridge Java and the target API",
            "caveat": "the split is by file name, not by parsing each diagnostic: treat the counts"
                      " as orientation, not as a verdict per error",
        },
        "scope": "compile probe only: no jar was converted, no rule was written, no game was launched",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"closure {closure_stats.get('jars')} jar(s) ({closure_stats.get('modules')} api modules)")
    print(f"bridge compile rc={probe.returncode} errors={len(err_lines)} classes={produced}")
    print(f"files with errors: {len(by_file)}; mod-api smell: {len(mod_related)}")
    print(f"-> {out / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
