#!/usr/bin/env python3
"""Compile the p194 third-atlas probe into work/tmp/p194-probe.jar (test-only, not committed)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "probes" / "p194-atlas-third"
SOURCES = sorted(str(q) for q in (PROBE / "src").rglob("*.java"))
META = PROBE / "fabric.mod.json"
CLIENT = ROOT / "work" / "launcher-e2e" / ".fabric" / "remappedJars" / "minecraft-1.21.1-0.19.5" / "client-intermediary.jar"
LOADER = (ROOT / "work" / "launcher-e2e" / "libraries" / "net" / "fabricmc" / "fabric-loader"
          / "0.19.5" / "fabric-loader-0.19.5.jar")
PORTED = ROOT / ".build" / "ImmediatelyFast-ported.jar"
LIFECYCLE = (ROOT / "work" / "launcher-e2e" / ".fabric" / "processedMods"
             / "fabric-lifecycle-events-v1-2.3.1+6c1df3606a-9f74236580e9e222.jar")
API_BASE = (ROOT / "work" / "launcher-e2e" / ".fabric" / "processedMods"
            / "fabric-api-base-0.4.42+6573ed8c6a-ec0e6648f37ee3.jar")
RENDERING = (ROOT / "work" / "launcher-e2e" / ".fabric" / "processedMods"
             / "fabric-rendering-v1-5.0.5+df16efd06a-659291bf00da8f39.jar")
MIXIN = (ROOT / "work" / "launcher-e2e" / "libraries" / "net" / "fabricmc" / "sponge-mixin"
         / "0.17.4+mixin.0.8.7" / "sponge-mixin-0.17.4+mixin.0.8.7.jar")
CLASSES = ROOT / "work" / "tmp" / "p194-probe-classes"
JAR = ROOT / "work" / "tmp" / "p194-probe.jar"


def main() -> int:
    java_home = os.environ.get("JAVA_HOME") or str(ROOT.parent / ".toolchain" / "jdk")
    javac = Path(java_home) / "bin" / ("javac.exe" if os.name == "nt" else "javac")
    for path in (javac, CLIENT, LOADER, PORTED, LIFECYCLE, API_BASE, RENDERING, MIXIN, META):
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 2
    if CLASSES.exists():
        shutil.rmtree(CLASSES)
    CLASSES.mkdir(parents=True)
    cp = os.pathsep.join([str(CLIENT), str(LOADER), str(PORTED), str(LIFECYCLE),
                          str(API_BASE), str(RENDERING), str(MIXIN)])
    rc = subprocess.call([str(javac), "-nowarn", "-proc:none", "-encoding", "UTF-8",
                          "-cp", cp, "-d", str(CLASSES)] + SOURCES)
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
        add("p194probe.mixins.json",
            (PROBE / "resources" / "p194probe.mixins.json").read_bytes())
        for path in sorted(CLASSES.rglob("*.class")):
            add(path.relative_to(CLASSES).as_posix(), path.read_bytes())
    print(f"probe jar: {JAR} ({JAR.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
