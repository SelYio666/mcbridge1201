#!/usr/bin/env python3
"""Compile the p190 multi-client trash probe into work/tmp/trashmulti.jar."""
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
CLIENT = ROOT / "work" / "launcher-e2e" / ".fabric" / "remappedJars" / "minecraft-1.21.1-0.19.5" / "client-intermediary.jar"
LOADER = (ROOT / "work" / "launcher-e2e" / "libraries" / "net" / "fabricmc" / "fabric-loader"
          / "0.19.5" / "fabric-loader-0.19.5.jar")
TRASH = ROOT / "work" / "client" / "trashslot-client-empty.jar"
BALM = (ROOT / "work" / "instances" / "fabric-1.21.1-server-trashslot" / "mods"
        / "balm-fabric-1.21.1.jar")
PROCESSED = ROOT / "work" / "launcher-e2e" / ".fabric" / "processedMods"
AUTHLIB = sorted((ROOT / "work" / "launcher-e2e" / "libraries" / "com" / "mojang"
                 / "authlib").rglob("authlib-*.jar"))[-1]
MIXIN = (ROOT / "work" / "launcher-e2e" / "libraries" / "net" / "fabricmc" / "sponge-mixin"
         / "0.17.4+mixin.0.8.7" / "sponge-mixin-0.17.4+mixin.0.8.7.jar")
CLASSES = ROOT / "work" / "tmp" / "trashmulti-classes"
JAR = ROOT / "work" / "tmp" / "trashmulti.jar"


def jar_files(directory: Path) -> list[str]:
    return [str(p) for p in sorted(directory.glob("*.jar"))] if directory.exists() else []


def main() -> int:
    java_home = os.environ.get("JAVA_HOME") or str(ROOT.parent / ".toolchain" / "jdk")
    javac = Path(java_home) / "bin" / ("javac.exe" if os.name == "nt" else "javac")
    for path in (javac, CLIENT, LOADER, TRASH, BALM, AUTHLIB):
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 2
    cp = [str(CLIENT), str(LOADER), str(TRASH), str(BALM), str(AUTHLIB), str(MIXIN)]
    cp += jar_files(PROCESSED)
    sources = sorted(str(p) for p in SRC.rglob("*.java"))
    if not sources:
        print("no probe sources", file=sys.stderr)
        return 2
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
            add(path.relative_to(CLASSES).as_posix(), path.read_bytes())
    print(f"probe jar: {JAR} ({JAR.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
