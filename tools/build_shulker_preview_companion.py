#!/usr/bin/env python3
"""Build the shulker preview companion mod.

The converted ShulkerBoxTooltip jar lost the mixin that supplied PreviewTooltipData from
ItemStack.getTooltipData (the old signature is gone in 1.21.1). This companion re-adds the wiring
through the current no-argument method, without editing the mod jar.

Usage:
    python tools/build_shulker_preview_companion.py --shulker <converted shulker jar> \
        --out work/client/sbtpreview.jar
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "java" / "src" / "shulkerpreview"


def run(cmd, env):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, env=env)


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


def find_library(name):
    base = ROOT / "work" / "launcher-e2e" / "libraries"
    jars = sorted(base.rglob(f"{name}*.jar"))
    if not jars:
        raise SystemExit(f"{name} jar not found")
    return jars[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shulker", required=True)
    ap.add_argument("--out", default=str(ROOT / "work" / "client" / "sbtpreview.jar"))
    ap.add_argument("--stub", default=str(ROOT / "work" / "cb" / "data" / "jars" / "client-1.21.1-intermediary.jar"))
    ap.add_argument("--java-home", default=os.environ.get("JAVA_HOME"))
    args = ap.parse_args()
    java_home = args.java_home
    if not java_home:
        raise SystemExit("JAVA_HOME not set")
    out_dir = ROOT / "work" / "tmp" / "sbtpreview-classes"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    cp = ";".join([args.stub, args.shulker, str(find_mixin_jar()), str(find_loader_jar()),
                   str(find_library("datafixerupper")), str(find_library("fastutil"))])
    processed = ROOT / "work" / "launcher-e2e" / ".fabric" / "processedMods"
    if processed.is_dir():
        cp += ";" + ";".join(str(p) for p in sorted(processed.glob("*.jar")))
    javac = Path(java_home) / "bin" / "javac.exe"
    sources = sorted(str(p) for p in (SRC / "java").rglob("*.java"))
    run([javac, "--release", "17", "-nowarn", "-proc:none", "-encoding", "UTF-8", "-cp", cp,
         "-d", str(out_dir)] + sources, dict(os.environ))
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
