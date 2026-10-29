"""Rebuild the Mod Menu list render bridge and drop it into the patched jar.

Only one bridge class changes this round, so the compile is targeted: `tools/build_bridges.py`
compiles every bridge source and needs the Fabric API / brigadier jars on the classpath, which are
not required to rebuild `ModMenuListRenderBridge` (it only touches `class_332`). The full pipeline
stays the canonical path; this is the narrow rebuild, and `tools/inject_bridges.py` is the supported
way to swap one bridge class in a jar that is otherwise unchanged.

Usage:
  python runs/p205-modmenu-rows/build.py [--skip-compile]
"""
import argparse
import hashlib
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
STUB = ROOT / "work" / "cb" / "data" / "jars" / "client-1.21.1-intermediary.jar"
SOURCE = ROOT / "java" / "src" / "bridge" / "java" / "top" / "mcbridge1201" / "bridge" / "ModMenuListRenderBridge.java"
CLASSES = ROOT / "work" / "tmp" / "p205-bridges"
BASE_JAR = ROOT / "work" / "client" / "modmenu-patched.jar"
OUT_JAR = ROOT / "work" / "client" / "modmenu-rows.jar"
BRIDGE = "top/mcbridge1201/bridge/ModMenuListRenderBridge"


def java_home() -> Path:
    env = os.environ.get("JAVA_HOME")
    if env:
        return Path(env)
    local = ROOT.parent / ".toolchain" / "jdk"
    if (local / "bin" / "javac.exe").is_file():
        return local
    raise SystemExit("JAVA_HOME is not set and there is no .toolchain/jdk next to the repo")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def class_bytes(jar: Path, internal: str) -> bytes:
    with zipfile.ZipFile(jar) as z:
        return z.read(internal + ".class")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-compile", action="store_true")
    args = ap.parse_args()

    log: list[str] = []

    def say(line: str) -> None:
        print(line)
        log.append(line)

    result = {"stub": str(STUB), "base_jar": str(BASE_JAR), "out_jar": str(OUT_JAR)}

    if not args.skip_compile:
        javac = java_home() / "bin" / ("javac.exe" if os.name == "nt" else "javac")
        if not javac.is_file():
            raise SystemExit(f"javac not found at {javac}")
        CLASSES.mkdir(parents=True, exist_ok=True)
        cmd = [str(javac), "-nowarn", "-proc:none", "-encoding", "UTF-8",
               "-J-Duser.language=en", "-J-Dfile.encoding=UTF-8",
               "-cp", str(STUB), "-d", str(CLASSES), str(SOURCE)]
        say("COMPILE " + " ".join(cmd))
        rc = subprocess.call(cmd)
        if rc != 0:
            say(f"COMPILE_FAILED rc={rc}")
            (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
            return rc

    fresh = CLASSES / "top" / "mcbridge1201" / "bridge" / "ModMenuListRenderBridge.class"
    if not fresh.is_file():
        raise SystemExit(f"compiled class missing: {fresh}")
    say(f"COMPILED {fresh} sha256={digest(fresh)}")

    for jar in (STUB, BASE_JAR):
        if not jar.is_file():
            raise SystemExit(f"missing input: {jar}")

    old = class_bytes(BASE_JAR, BRIDGE)
    say(f"BEFORE  {BRIDGE}.class in {BASE_JAR.name} sha256={hashlib.sha256(old).hexdigest()}"
        f" size={len(old)}")

    inject = [sys.executable, str(ROOT / "tools" / "inject_bridges.py"),
              "--jar", str(BASE_JAR), "--out", str(OUT_JAR),
              "--classes", str(CLASSES), "--replace", BRIDGE]
    say("INJECT " + " ".join(inject))
    rc = subprocess.call(inject)
    if rc != 0:
        say(f"INJECT_FAILED rc={rc}")
        (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
        return rc

    new = class_bytes(OUT_JAR, BRIDGE)
    say(f"AFTER   {BRIDGE}.class in {OUT_JAR.name} sha256={hashlib.sha256(new).hexdigest()}"
        f" size={len(new)}")
    if new == old:
        raise SystemExit("bridge class is byte-identical to the old one; nothing was replaced")
    say(f"OUT {OUT_JAR} sha256={digest(OUT_JAR)} size={OUT_JAR.stat().st_size}")
    (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
