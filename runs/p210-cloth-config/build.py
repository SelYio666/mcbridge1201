"""Build the AppleSkin jar whose nested Cloth Config no longer reads a 1.21.1-removed field (p210).

Cloth Config is not a mod in this setup: it is a jar-in-jar inside AppleSkin
(`META-INF/jars/cloth-config-fabric-11.1.136.jar`). So there is nothing to point the patcher at
directly - the jar has to be taken out, patched, and put back:

1. `javac` the bridge (`ClothConfigBridge.defaultBackground`) against the 1.21.1 intermediary stub.
2. Extract the nested cloth jar from `appleskin-patched.jar` (the converted AppleSkin already in
   `work/client/`), patch it with `cloth-config.json`, and require the rule to report exactly one
   hit - a silent no-op here would ship the old crash.
3. Write a new AppleSkin jar with that entry replaced. Everything else in the outer jar, including
   its other entries and the second nested cloth jar inside ShulkerBoxTooltip's copy, is untouched:
   this run patches the copy the loader actually resolves (the log lists cloth-config 11.1.136).

Output goes to `work/client/appleskin-cloth.jar`; `appleskin-patched.jar` is left alone so the
p204-p209 evidence still reproduces against the jar those runs used.

Usage:
  python runs/p210-cloth-config/build.py [--skip-compile]
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
STUB = ROOT / "work" / "cb" / "data" / "jars" / "client-1.21.1-intermediary.jar"
MAPPINGS = ROOT / "work" / "cb" / "data" / "mappings" / "intermediary-1.21.1.tiny"
BRIDGE_SRC = ROOT / "java" / "src" / "bridge" / "java" / "top" / "mcbridge1201" / "bridge"
SOURCES = [BRIDGE_SRC / "ClothConfigBridge.java",
           BRIDGE_SRC / "ClothTextFieldBridge.java",
           BRIDGE_SRC / "ClothConfigScreenBridge.java",
           BRIDGE_SRC / "ClothRenderBridge.java"]
CLASSES = ROOT / "work" / "tmp" / "p210-bridges"
WORK = ROOT / "work" / "tmp" / "p210"
BASE_JAR = ROOT / "work" / "client" / "appleskin-patched.jar"
CLOTH_ENTRY = "META-INF/jars/cloth-config-fabric-11.1.136.jar"
EXTRACTED = WORK / "cloth-in.jar"
PATCHED = WORK / "cloth-patched.jar"
OUT_JAR = ROOT / "work" / "client" / "appleskin-cloth.jar"
# This jar is raw 1.20.1 Cloth Config, so it also needs the generic rules that every converted
# mod gets. The one that matters here is render-widget-override: Cloth declares 12 overrides of
# method_25394, which 1.21.1 made final on ClickableWidget, and each one is a class-load
# IncompatibleClassChangeError (the first run of this harness died on TextFieldListEntry$1 before
# printing a single option row).
RULES = [
    ROOT / "rules" / "fabric-1.21.1" / "render-widget-override.json",
    ROOT / "rules" / "fabric-1.21.1" / "cloth-config.json",
    ROOT / "rules" / "fabric-1.21.1" / "cloth-config-render.json",
]
INSTALL = ROOT / "java" / "build" / "install" / "mcbridge1201"
RULE_ID = "cloth-config.screen-background"
FIELD = b"field_44669"
# Every rule that must report exactly one hit, keyed to the id the patcher prints. A no-op here
# would ship the crash this run exists to remove, so each one is asserted rather than eyeballed.
MUST_HIT_ONCE = [
    "cloth-config.screen-background",
    "cloth-config.textfield.cursor-to-start",
    "cloth-config.textfield.set-cursor",
    "cloth-config.screen.render-background.clothconfigscreen",
    "cloth-config.screen.render-background.globalizedclothconfigscreen",
    "cloth-config.render.textfield-tick",
    "cloth-config.render.demo-item-name",
    "cloth-config.render.demo-enchantment",
    "cloth-config.render.demo-add-enchantment",
    "cloth-config.render.list-backdrop",
    "cloth-config.render.list-vignette",
    "cloth-config.render.screen-overlay",
    "cloth-config.render.tab-shades",
    "cloth-config.render.fill-gradient",
    "cloth-config.render.dropdown-shadow",
]
BRIDGE_CLASSES = ["ClothConfigBridge", "ClothTextFieldBridge", "ClothConfigScreenBridge",
                  "ClothRenderBridge"]


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


def write_entry(dst: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    dst.writestr(info, data)


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
    WORK.mkdir(parents=True, exist_ok=True)

    if not args.skip_compile:
        CLASSES.mkdir(parents=True, exist_ok=True)
        cmd = [str(javac), "-nowarn", "-proc:none", "-encoding", "UTF-8",
               "-J-Duser.language=en", "-J-Dfile.encoding=UTF-8",
               "-cp", str(STUB), "-d", str(CLASSES)] + [str(x) for x in SOURCES]
        say("COMPILE " + " ".join(cmd))
        rc = subprocess.call(cmd)
        if rc != 0:
            say(f"COMPILE_FAILED rc={rc}")
            (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
            return rc

    for name in [b + ".class" for b in BRIDGE_CLASSES]:
        compiled = CLASSES / "top" / "mcbridge1201" / "bridge" / name
        if not compiled.is_file():
            raise SystemExit(f"compiled class missing: {compiled}")
        say(f"COMPILED {name} sha256={digest(compiled)} size={compiled.stat().st_size}")

    if not BASE_JAR.is_file():
        raise SystemExit(f"missing input: {BASE_JAR}")
    say(f"BASE {BASE_JAR.name} sha256={digest(BASE_JAR)} size={BASE_JAR.stat().st_size}")

    with zipfile.ZipFile(BASE_JAR) as src:
        if CLOTH_ENTRY not in src.namelist():
            raise SystemExit(f"{BASE_JAR.name} has no {CLOTH_ENTRY}")
        cloth = src.read(CLOTH_ENTRY)
    say(f"NESTED {CLOTH_ENTRY} sha256={hashlib.sha256(cloth).hexdigest()} size={len(cloth)}")
    EXTRACTED.write_bytes(cloth)
    # The bytes above are deflated, so searching them for a field name proves nothing. Read the one
    # class the rule targets, uncompressed: if it no longer mentions field_44669 it is already
    # patched (or is not 11.1.136), and silently shipping it would ship the crash this run exists
    # to remove.
    with zipfile.ZipFile(EXTRACTED) as z:
        target = "me/shedaniel/clothconfig2/impl/ConfigBuilderImpl.class"
        if target not in z.namelist():
            raise SystemExit(f"{CLOTH_ENTRY} has no {target}")
        impl = z.read(target)
    say(f"TARGET {target} sha256={hashlib.sha256(impl).hexdigest()} size={len(impl)}"
        f" mentionsField={FIELD in impl}")
    if FIELD not in impl:
        raise SystemExit("the nested ConfigBuilderImpl does not mention field_44669; "
                         "either it is already patched or it is not the jar this rule targets")

    patch = [str(java), "-cp", str(INSTALL / "lib" / "*"), "top.mcbridge1201.Main", "patch",
             "--in", str(EXTRACTED), "--out", str(PATCHED)]
    for rule_file in RULES:
        patch += ["--rules", str(rule_file)]
    patch += ["--bridge-dir", str(CLASSES)]
    # render-widget-override carries onlyIfExtends, which has to resolve ClickableWidget through
    # the client jar: Cloth's classes chain into Minecraft (class_362) and the rename must be
    # decided on the real ancestors, not guessed.
    patch += ["--client-jar", str(STUB), "--mappings", str(MAPPINGS)]
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
    if f"{RULE_ID} applied 1 time(s)" not in (proc.stdout or ""):
        say("PATCH_DID_NOT_APPLY the background rule did not report exactly one hit")
        (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
        return 1
    missing = [rid for rid in MUST_HIT_ONCE
               if f"{rid} applied 1 time(s)" not in (proc.stdout or "")]
    if missing:
        say("PATCH_DID_NOT_APPLY these rules did not report exactly one hit: " + ", ".join(missing))
        (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
        return 1
    # buffer-accessor is the one rule whose count is not 1: it also retargets the three live t0
    # calls left in GlobalizedClothConfigScreen.method_25394, which this run does not otherwise
    # touch. See the rule note for why that screen stays broken.
    if "cloth-config.render.buffer-accessor applied" not in (proc.stdout or ""):
        say("PATCH_DID_NOT_APPLY the buffer-accessor rule never hit")
        (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
        return 1
    if "fabric.legacy.render-widget-override applied" not in (proc.stdout or ""):
        say("PATCH_DID_NOT_APPLY the render-override rule never hit; the jar would fail to load")
        (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
        return 1

    patched_cloth = PATCHED.read_bytes()
    say(f"PATCHED {PATCHED.name} sha256={hashlib.sha256(patched_cloth).hexdigest()}"
        f" size={len(patched_cloth)}")
    with zipfile.ZipFile(PATCHED) as z:
        names = set(z.namelist())
    for bridge_entry in [f"top/mcbridge1201/bridge/{b}.class" for b in BRIDGE_CLASSES]:
        if bridge_entry not in names:
            raise SystemExit(f"the patched cloth jar does not carry {bridge_entry}")
        say(f"EMBEDDED {bridge_entry} present")

    with zipfile.ZipFile(BASE_JAR) as src, zipfile.ZipFile(OUT_JAR, "w") as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == CLOTH_ENTRY:
                data = patched_cloth
            write_entry(dst, item.filename, data)
    say(f"OUT {OUT_JAR.name} sha256={digest(OUT_JAR)} size={OUT_JAR.stat().st_size}")
    (RUN / "build.log").write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
