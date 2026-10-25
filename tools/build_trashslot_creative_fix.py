#!/usr/bin/env python3
"""Build the TrashSlot creative-delete companion (1.21.1 adaptation).

The 1.21.1 creative screen keeps AbstractContainerScreen.hoveredSlot null and has no SlotWrapper,
so the converted TrashSlot's creative delete branch can never run. This companion re-implements
the branch (companion mixin on TrashSlotGuiHandler.runKeyBindings).

Usage:
    python tools/build_trashslot_creative_fix.py --trashslot work/client/trashslot-client-empty.jar \
        --out work/client/trashcreative-fix.jar
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "java" / "src" / "trashcreative"


def find_mixin_jar():
    base = Path(r"D:\我的世界\.minecraft\libraries\net\fabricmc\sponge-mixin")
    jars = sorted(base.rglob("sponge-mixin-0.17*.jar"))
    if not jars:
        raise SystemExit("sponge-mixin jar not found")
    return jars[-1]


def find_loader_jar():
    base = ROOT / "work" / "launcher-e2e" / "libraries" / "net" / "fabricmc" / "fabric-loader"
    jars = sorted(base.rglob("fabric-loader-*.jar"))
    if not jars:
        raise SystemExit("fabric-loader jar not found")
    return jars[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trashslot", required=True, help="converted TrashSlot jar (class reference)")
    ap.add_argument("--balm", default=str(ROOT / "work" / "instances"
                                           / "fabric-1.21.1-server-trashslot" / "mods"
                                           / "balm-fabric-1.21.1.jar"))
    ap.add_argument("--stub", default=str(ROOT / "work" / "cb" / "data" / "jars"
                                           / "client-1.21.1-intermediary.jar"))
    ap.add_argument("--out", default=str(ROOT / "work" / "client" / "trashcreative-fix.jar"))
    ap.add_argument("--java-home", default=os.environ.get("JAVA_HOME"))
    args = ap.parse_args()
    if not args.java_home:
        raise SystemExit("JAVA_HOME not set")
    out_dir = ROOT / "work" / "tmp" / "trashcreative-fix-classes"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    # kuma-api ships nested inside the balm jar; extract it for the compile classpath.
    kuma_dir = ROOT / "work" / "tmp" / "kuma-nested"
    kuma_dir.mkdir(parents=True, exist_ok=True)
    kuma_jar = None
    import zipfile
    with zipfile.ZipFile(args.balm) as bf:
        for name in bf.namelist():
            if "kuma" in name.lower() and name.endswith(".jar"):
                (kuma_dir / name.split("/")[-1]).write_bytes(bf.read(name))
                kuma_jar = kuma_dir / name.split("/")[-1]
    processed = ROOT / "work" / "launcher-e2e" / ".fabric" / "processedMods"
    jars = [args.stub, args.trashslot, args.balm,
            str(find_mixin_jar()), str(find_loader_jar())]
    if kuma_jar:
        jars.append(str(kuma_jar))
    if processed.is_dir():
        jars.extend(str(p) for p in sorted(processed.glob("*.jar")))
    cp = ";".join(jars)
    javac = Path(args.java_home) / "bin" / "javac.exe"
    sources = sorted(str(p) for p in (SRC / "java").rglob("*.java"))
    print("+", javac.name, *sources)
    subprocess.run([str(javac), "--release", "17", "-nowarn", "-proc:none", "-encoding", "UTF-8",
                    "-cp", cp, "-d", str(out_dir)] + sources, check=True)
    resources = SRC / "resources"
    for item in resources.iterdir():
        shutil.copy2(item, out_dir / item.name)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in out_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(out_dir).as_posix())
    print("built", out)


if __name__ == "__main__":
    main()
