#!/usr/bin/env python3
"""Compile the ImmediatelyFast 1.21.1 port sources against the intermediary client jar.

The port lives in java/src/compat/java/net/raphimc/immediatelyfast and uses intermediary
(class_XXXX) names, so it needs the intermediary-named 1.21.1 client jar plus fastutil.

Usage:
  python tools/build_immediatelyfast_port.py
  python tools/build_immediatelyfast_port.py --out work/tmp/if-port-classes
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "java" / "src" / "compat" / "java" / "net" / "raphimc" / "immediatelyfast"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intermediary",
                    default=str(ROOT / "work" / "cb" / "data" / "jars"
                               / "client-1.21.1-intermediary.jar"))
    ap.add_argument("--fastutil",
                    default=str(ROOT / "work" / "launcher-e2e" / "libraries" / "it" / "unimi"
                               / "dsi" / "fastutil" / "8.5.12" / "fastutil-8.5.12.jar"))
    ap.add_argument("--mixin",
                    default=str(ROOT / "work" / "launcher-e2e" / "libraries" / "net" / "fabricmc"
                               / "sponge-mixin" / "0.16.4+mixin.0.8.7"
                               / "sponge-mixin-0.16.4+mixin.0.8.7.jar"))
    ap.add_argument("--joml",
                    default=str(ROOT / "work" / "launcher-e2e" / "libraries" / "org" / "joml"
                               / "joml" / "1.10.5" / "joml-1.10.5.jar"))
    ap.add_argument("--mod-jar",
                    default=str(ROOT / "work" / "cb" / "out" / "popular" / "immediatelyfast"
                               / "ImmediatelyFast-Fabric-1.5.5+1.20.4+1.21.1.jar"))
    ap.add_argument("--out", default=str(ROOT / "work" / "tmp" / "if-port-classes"))
    args = ap.parse_args()

    java_home = os.environ.get("JAVA_HOME") or str(ROOT.parent / ".toolchain" / "jdk")
    javac = Path(java_home) / "bin" / ("javac.exe" if os.name == "nt" else "javac")
    if not javac.exists():
        print(f"javac not found: {javac}", file=sys.stderr)
        return 2
    cp_jars = [args.intermediary, args.fastutil, args.mixin, args.joml, args.mod_jar]
    for jar in cp_jars:
        if not Path(jar).exists():
            print(f"missing classpath jar: {jar}", file=sys.stderr)
            return 2
    sources = sorted(str(p) for p in SRC.rglob("*.java"))
    if not sources:
        print(f"no port sources under {SRC}", file=sys.stderr)
        return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cp = os.pathsep.join(cp_jars)
    cmd = [str(javac), "-nowarn", "-proc:none", "-encoding", "UTF-8", "-cp", cp,
           "-d", str(out)] + sources
    print(" ".join(cmd))
    rc = subprocess.call(cmd)
    print(f"javac exit: {rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
