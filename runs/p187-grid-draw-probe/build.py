#!/usr/bin/env python3
"""Compile the p187 grid draw probe (probe entrypoint + BasePreviewRenderer tracer mixins)
into work/tmp/gridprobe187.jar."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
SRC = RUN / "src"
META = RUN / "fabric.mod.json"
MIXINS = RUN / "resources" / "sbtprobe.mixins.json"
CLIENT = (ROOT / "work" / "launcher-e2e" / ".fabric" / "remappedJars"
          / "minecraft-1.21.1-0.19.5" / "client-intermediary.jar")
LOADER = (ROOT / "work" / "launcher-e2e" / "libraries" / "net" / "fabricmc" / "fabric-loader"
          / "0.19.5" / "fabric-loader-0.19.5.jar")
BALM = ROOT / "work" / "corpus" / "deps" / "balm-fabric-1.21.1-21.0.66.jar"
SHULKER = ROOT / "work" / "client" / "shulker-patched2.jar"
SPONGE = sorted(Path(r"D:\我的世界\.minecraft\libraries\net\fabricmc\sponge-mixin")
                .rglob("sponge-mixin-0.17*.jar"))
DATAFIXER = (ROOT / "work" / "launcher-e2e" / "libraries" / "com" / "mojang" / "datafixerupper"
             / "8.0.16" / "datafixerupper-8.0.16.jar")
FASTUTIL = (ROOT / "work" / "launcher-e2e" / "libraries" / "it" / "unimi" / "dsi" / "fastutil"
            / "8.5.12" / "fastutil-8.5.12.jar")
PROCESSED = ROOT / "work" / "launcher-e2e" / ".fabric" / "processedMods"
CLASSES = ROOT / "work" / "tmp" / "gridprobe187-classes"
JAR = ROOT / "work" / "tmp" / "gridprobe187.jar"


def main() -> int:
    java_home = os.environ.get("JAVA_HOME") or str(ROOT.parent / ".toolchain" / "jdk")
    javac = Path(java_home) / "bin" / ("javac.exe" if os.name == "nt" else "javac")
    if not SPONGE:
        print("sponge-mixin jar not found under D:\\我的世界\\.minecraft\\libraries", file=sys.stderr)
        return 2
    cp = [str(CLIENT), str(LOADER), str(BALM), str(SHULKER), str(SPONGE[-1]),
          str(DATAFIXER), str(FASTUTIL)] + [str(p) for p in PROCESSED.glob("*.jar")]
    sources = sorted(str(p) for p in SRC.rglob("*.java"))
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
        add("sbtprobe.mixins.json", MIXINS.read_bytes())
        for path in sorted(CLASSES.rglob("*.class")):
            add(path.relative_to(CLASSES).as_posix(), path.read_bytes())
    print(f"probe jar: {JAR} ({JAR.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
