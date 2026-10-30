"""Build the Mod Menu jar whose scrollbar branch is observable (p209).

Only one class changes relative to p207: `ModMenuListRenderBridge`. p207 shipped without ever
reaching its scrollbar branch (`maxScroll=0`, no description long enough at 1280x720), so the debug
line sat *after* the early return and could not tell "nothing to scroll" from "never rendered".
This build compiles the bridge with that line moved before the branch, reported on change, and
swaps it into a copy of `modmenu-description.jar`.

Nothing else is re-patched: the two jars differ in exactly one class entry, which is checked here
and again in `verify_scroll.py`. The p205/p206/p207 jars are left untouched so their recorded
sha256 still match the files on disk.

Usage:
  python runs/p209-description-scroll/build.py [--skip-compile]
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
BRIDGE_SRC = ROOT / "java" / "src" / "bridge" / "java" / "top" / "mcbridge1201" / "bridge"
SOURCES = [BRIDGE_SRC / "ModMenuListRenderBridge.java"]
CLASSES = ROOT / "work" / "tmp" / "p209-bridges"
BASE_JAR = ROOT / "work" / "client" / "modmenu-description.jar"
OUT_JAR = ROOT / "work" / "client" / "modmenu-scroll.jar"
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


def entries(jar: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(jar) as z:
        return {n: z.read(n) for n in z.namelist() if not n.endswith("/")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-compile", action="store_true")
    args = ap.parse_args()

    log: list[str] = []

    def say(line: str) -> None:
        print(line)
        log.append(line)

    def flush(rc: int) -> int:
        (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
        return rc

    home = java_home()
    javac = home / "bin" / ("javac.exe" if os.name == "nt" else "javac")

    for need in (STUB, BASE_JAR):
        if not need.is_file():
            raise SystemExit(f"missing input: {need}; build p207 first")

    if not args.skip_compile:
        if not javac.is_file():
            raise SystemExit(f"javac not found at {javac}")
        CLASSES.mkdir(parents=True, exist_ok=True)
        cmd = [str(javac), "-nowarn", "-proc:none", "-encoding", "UTF-8",
               "-J-Duser.language=en", "-J-Dfile.encoding=UTF-8",
               "-cp", str(STUB), "-d", str(CLASSES)] + [str(s) for s in SOURCES]
        say("COMPILE " + " ".join(cmd))
        rc = subprocess.call(cmd)
        if rc != 0:
            say(f"COMPILE_FAILED rc={rc}")
            return flush(rc)

    fresh = CLASSES / "top" / "mcbridge1201" / "bridge" / "ModMenuListRenderBridge.class"
    if not fresh.is_file():
        raise SystemExit(f"compiled class missing: {fresh}")
    say(f"COMPILED {fresh.name} sha256={digest(fresh)} size={fresh.stat().st_size}")
    if b"P207_SCROLL" not in fresh.read_bytes():
        say("COMPILED_WITHOUT_SCROLL_LINE refusing to ship a bridge that cannot report scrolling")
        return flush(1)

    old = entries(BASE_JAR)[BRIDGE + ".class"]
    say(f"BASE     {BRIDGE} from {BASE_JAR.name} sha256={hashlib.sha256(old).hexdigest()}"
        f" size={len(old)}")

    inject = [sys.executable, str(ROOT / "tools" / "inject_bridges.py"),
              "--jar", str(BASE_JAR), "--out", str(OUT_JAR),
              "--classes", str(CLASSES), "--replace", BRIDGE]
    say("INJECT " + " ".join(inject))
    rc = subprocess.call(inject)
    if rc != 0:
        say(f"INJECT_FAILED rc={rc}")
        return flush(rc)

    # p207's evidence is tied to its jar, so this build must not have touched anything else.
    after = entries(OUT_JAR)
    before = entries(BASE_JAR)
    changed = sorted(n for n in before if n in after and before[n] != after[n])
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    say("DIFF changed=" + (", ".join(changed) or "none")
        + " added=" + (", ".join(added) or "none")
        + " removed=" + (", ".join(removed) or "none"))
    if changed != [BRIDGE + ".class"] or added or removed:
        say("DIFF_UNEXPECTED the output differs from the p207 jar in more than the bridge")
        return flush(1)

    say(f"OUT {OUT_JAR.name} sha256={digest(OUT_JAR)} size={OUT_JAR.stat().st_size}")
    return flush(0)


if __name__ == "__main__":
    sys.exit(main())
