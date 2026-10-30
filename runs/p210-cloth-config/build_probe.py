#!/usr/bin/env python3
"""Compile the p210 Cloth Config probe into work/tmp/p210probe.jar.

Same dependency set as the p204 probe (client intermediary + loader + mixin + fabric transitive
jars): the probe only touches Screen/TitleScreen/Client and reaches Mod Menu reflectively, so it
needs no mod classpath of its own.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "probes" / "p210-cloth-config" / "src"
META = ROOT / "probes" / "p210-cloth-config" / "fabric.mod.json"
CLIENT = (ROOT / "work" / "launcher-e2e" / ".fabric" / "remappedJars"
          / "minecraft-1.21.1-0.19.5" / "client-intermediary.jar")
LOADER = (ROOT / "work" / "launcher-e2e" / "libraries" / "net" / "fabricmc" / "fabric-loader"
          / "0.19.5" / "fabric-loader-0.19.5.jar")
MIXIN = (ROOT / "work" / "launcher-e2e" / "libraries" / "net" / "fabricmc" / "sponge-mixin"
         / "0.17.4+mixin.0.8.7" / "sponge-mixin-0.17.4+mixin.0.8.7.jar")
DATAFIXER = (ROOT / "work" / "launcher-e2e" / "libraries" / "com" / "mojang" / "datafixerupper"
             / "8.0.16" / "datafixerupper-8.0.16.jar")
FASTUTIL = (ROOT / "work" / "launcher-e2e" / "libraries" / "it" / "unimi" / "dsi" / "fastutil"
            / "8.5.12" / "fastutil-8.5.12.jar")
LWJGL = ROOT / "work" / "launcher-e2e" / "libraries" / "org" / "lwjgl" / "lwjgl" / "3.3.3" \
    / "lwjgl-3.3.3.jar"
GLFW = ROOT / "work" / "launcher-e2e" / "libraries" / "org" / "lwjgl" / "lwjgl-glfw" / "3.3.3" \
    / "lwjgl-glfw-3.3.3.jar"
PROCESSED = ROOT / "work" / "launcher-e2e" / ".fabric" / "processedMods"
CLASSES = ROOT / "work" / "tmp" / "p210probe-classes"
JAR = ROOT / "work" / "tmp" / "p210probe.jar"


def main() -> int:
    java_home = os.environ.get("JAVA_HOME") or str(ROOT.parent / ".toolchain" / "jdk")
    javac = Path(java_home) / "bin" / ("javac.exe" if os.name == "nt" else "javac")
    for path in (MIXIN, LWJGL, GLFW):
        if not path.exists():
            print(f"missing dependency: {path}", file=sys.stderr)
            return 2
    cp = [str(CLIENT), str(LOADER), str(MIXIN), str(DATAFIXER), str(FASTUTIL),
          str(LWJGL), str(GLFW)]
    cp += [str(p) for p in PROCESSED.glob("*.jar")]
    sources = sorted(str(q) for q in SRC.rglob("*.java"))
    if CLASSES.exists():
        shutil.rmtree(CLASSES)
    CLASSES.mkdir(parents=True)
    rc = subprocess.call([str(javac), "-nowarn", "-proc:none", "-encoding", "UTF-8",
                          "--release", "17", "-cp", os.pathsep.join(cp),
                          "-d", str(CLASSES)] + sources)
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
            add(str(path.relative_to(CLASSES)).replace(os.sep, "/"), path.read_bytes())
    print(f"jar written: {JAR} ({JAR.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
