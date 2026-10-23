#!/usr/bin/env python3
"""Compile the p181 disconnect probe into work/tmp/p181-probe.jar (test-only, not committed)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "probes" / "p181-disconnect"
SRC = PROBE / "src" / "p181probe" / "DisconnectProbe.java"
META = PROBE / "fabric.mod.json"
CLIENT = ROOT / "work" / "launcher-e2e" / ".fabric" / "remappedJars" / "minecraft-1.21.1-0.19.5" / "client-intermediary.jar"
LOADER = (ROOT / "work" / "launcher-e2e" / "libraries" / "net" / "fabricmc" / "fabric-loader"
          / "0.19.5" / "fabric-loader-0.19.5.jar")
CLASSES = ROOT / "work" / "tmp" / "p181-probe-classes"
JAR = ROOT / "work" / "tmp" / "p181-probe.jar"


def main() -> int:
    java_home = os.environ.get("JAVA_HOME") or str(ROOT.parent / ".toolchain" / "jdk")
    javac = Path(java_home) / "bin" / ("javac.exe" if os.name == "nt" else "javac")
    for path in (javac, CLIENT, LOADER, SRC, META):
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 2
    if CLASSES.exists():
        shutil.rmtree(CLASSES)
    CLASSES.mkdir(parents=True)
    cp = os.pathsep.join([str(CLIENT), str(LOADER)])
    rc = subprocess.call([str(javac), "-nowarn", "-proc:none", "-encoding", "UTF-8",
                          "-cp", cp, "-d", str(CLASSES), str(SRC)])
    print(f"javac exit: {rc}")
    if rc != 0:
        return rc
    JAR.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(JAR, "w", zipfile.ZIP_DEFLATED) as zout:
        def add(name: str, data: bytes) -> None:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(info, data)
        add("fabric.mod.json", META.read_bytes())
        for path in sorted(CLASSES.rglob("*.class")):
            add(path.relative_to(CLASSES).as_posix(), path.read_bytes())
    print(f"probe jar: {JAR} ({JAR.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
