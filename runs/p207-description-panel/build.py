"""Build the Mod Menu jar whose description panel keeps its rows (p207).

Three steps, all recorded in build.log:

1. `javac` the bridge (renderList + the new renderDescription) against the 1.21.1 intermediary
   stub, exactly like p205/p206.
2. Put the pre-redirect `DescriptionListWidget.class` back into a copy of `modmenu-patched.jar`.
   The p206 jar has that class with its body wiped, and the body - which builds the description
   rows - is not recoverable from it. The pristine copy is the one in `modmenu-instrumented.jar`;
   `verify_description.py` re-checks that its `method_48579` is byte-for-byte the method recorded in
   `runs/p206-modmenu-select/bytecode/render-original.txt` before this build is allowed to count.
3. Run the patcher with `modmenu-list-render.json` so the new `keepPrefixBeforeTombstones` rule cuts
   only the removed-API tail and appends `ModMenuListRenderBridge.renderDescription`.

Output goes to `work/client/modmenu-description.jar`; the p205/p206 jars are left untouched so their
recorded sha256 still match the files on disk.

Usage:
  python runs/p207-description-panel/build.py [--skip-compile]
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
SOURCES = [BRIDGE_SRC / "ModMenuListRenderBridge.java", BRIDGE_SRC / "LegacyParentWidget.java"]
CLASSES = ROOT / "work" / "tmp" / "p207-bridges"
BASE_JAR = ROOT / "work" / "client" / "modmenu-patched.jar"
PRISTINE_JAR = ROOT / "work" / "client" / "modmenu-instrumented.jar"
RESTORED_JAR = ROOT / "work" / "tmp" / "p207" / "restored.jar"
PATCHED_JAR = ROOT / "work" / "tmp" / "p207" / "patched.jar"
OUT_JAR = ROOT / "work" / "client" / "modmenu-description.jar"
RULES = ROOT / "rules" / "fabric-1.21.1" / "modmenu-list-render.json"
INSTALL = ROOT / "java" / "build" / "install" / "mcbridge1201"
BRIDGE = "top/mcbridge1201/bridge/ModMenuListRenderBridge"
LEGACY = "top/mcbridge1201/bridge/LegacyParentWidget"
PANEL = "com/terraformersmc/modmenu/gui/widget/DescriptionListWidget"


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


def entry(jar: Path, internal: str) -> bytes:
    with zipfile.ZipFile(jar) as z:
        return z.read(internal + ".class")


def restore_description_class() -> None:
    """Write a copy of the p206 jar in which one class is the pre-redirect original."""
    RESTORED_JAR.parent.mkdir(parents=True, exist_ok=True)
    pristine = entry(PRISTINE_JAR, PANEL)
    if b"println" in pristine:
        raise SystemExit("the pristine DescriptionListWidget carries a println; refusing to ship it")
    if b"centurybridge/gen/" not in pristine:
        raise SystemExit("the pristine DescriptionListWidget has no tombstone reference; "
                         "it is not the pre-redirect body")
    with zipfile.ZipFile(BASE_JAR) as src, zipfile.ZipFile(RESTORED_JAR, "w") as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == PANEL + ".class":
                data = pristine
            zi = zipfile.ZipInfo(item.filename, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            dst.writestr(zi, data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-compile", action="store_true")
    args = ap.parse_args()

    log: list[str] = []

    def say(line: str) -> None:
        print(line)
        log.append(line)

    home = java_home()
    javac = home / "bin" / ("javac.exe" if os.name == "nt" else "javac")
    java = home / "bin" / ("java.exe" if os.name == "nt" else "java")

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
            (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
            return rc

    fresh = CLASSES / "top" / "mcbridge1201" / "bridge" / "ModMenuListRenderBridge.class"
    legacy = CLASSES / "top" / "mcbridge1201" / "bridge" / "LegacyParentWidget.class"
    for need in (fresh, legacy):
        if not need.is_file():
            raise SystemExit(f"compiled class missing: {need}")
    say(f"COMPILED {fresh.name} sha256={digest(fresh)} size={fresh.stat().st_size}")
    say(f"COMPILED {legacy.name} sha256={digest(legacy)} size={legacy.stat().st_size}")

    for jar in (STUB, BASE_JAR, PRISTINE_JAR):
        if not jar.is_file():
            raise SystemExit(f"missing input: {jar}")

    pristine = entry(PRISTINE_JAR, PANEL)
    say(f"PRISTINE {PANEL} from {PRISTINE_JAR.name} sha256={hashlib.sha256(pristine).hexdigest()}"
        f" size={len(pristine)}")
    say(f"BASE     {PANEL} from {BASE_JAR.name} sha256="
        f"{hashlib.sha256(entry(BASE_JAR, PANEL)).hexdigest()} size={len(entry(BASE_JAR, PANEL))}")

    restore_description_class()
    say(f"RESTORED {RESTORED_JAR} sha256={digest(RESTORED_JAR)}"
        f" size={RESTORED_JAR.stat().st_size}")

    patch = [str(java), "-cp", str(INSTALL / "lib" / "*"), "top.mcbridge1201.Main", "patch",
             "--in", str(RESTORED_JAR), "--out", str(PATCHED_JAR), "--rules", str(RULES),
             "--bridge-dir", str(CLASSES)]
    say("PATCH " + " ".join(patch))
    proc = subprocess.run(patch, capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (proc.stdout or "").splitlines():
        say("  " + line)
    if proc.returncode != 0:
        for line in (proc.stderr or "").splitlines():
            say("  STDERR " + line)
        say(f"PATCH_FAILED rc={proc.returncode}")
        (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
        return proc.returncode

    if "modmenu.description.render-tail-renamed applied 1 time(s)" not in (proc.stdout or ""):
        say("PATCH_DID_NOT_APPLY the description rule did not report a hit")
        (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
        return 1

    # LegacyParentWidget is a superclass the rules do not reference, so the patcher does not embed
    # it; the javac build of it is swapped in the same way p205/p206 swapped their bridge.
    inject = [sys.executable, str(ROOT / "tools" / "inject_bridges.py"),
              "--jar", str(PATCHED_JAR), "--out", str(OUT_JAR),
              "--classes", str(CLASSES), "--replace", LEGACY]
    say("INJECT " + " ".join(inject))
    rc = subprocess.call(inject)
    if rc != 0:
        say(f"INJECT_FAILED rc={rc}")
        (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
        return rc

    say(f"OUT {OUT_JAR.name} sha256={digest(OUT_JAR)} size={OUT_JAR.stat().st_size}")
    (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
