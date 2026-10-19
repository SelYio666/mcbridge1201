#!/usr/bin/env python3
"""Rebuild the patched IronChests client jar from the converted + model-shim jar.

Pipeline (each step is the same one that was verified by hand in runs/p68-p70):

1. apply the sync-NBT rules (ironchests-nbt + nbt-packet);
2. replace the three ResourcefulLib networking classes inside the nested
   META-INF/jars/resourcefullib-fabric-1.20-2.0.6.jar;
3. apply the screen + draw rules to the outer jar.

Usage:
    python tools/rebuild_ironchests_client.py \
        --fabric-api "D:/.../fabric-api-0.102.0+1.21.1.jar" \
        --out work/client/ironchests-rebuilt.jar

JAVA_HOME must point at a JDK (the patch CLI and javac both use it).
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "rules" / "fabric-1.21.1"
RL_PACKAGE = "com/teamresourceful/resourcefullib/common/networking/fabric/"
RL_CLASSES = [
    "PacketChannelHelperImpl.class",
    "FabricClientPacketHelper.class",
    "FabricClientPacketHelper$RawPayload.class",
]
NESTED = "META-INF/jars/resourcefullib-fabric-1.20-2.0.6.jar"


def run(cmd, env):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, env=env)


def patch(src, dst, rules, bridges, java_home):
    cmd = [
        str(ROOT / "java" / "build" / "install" / "mcbridge1201" / "bin" / "mcbridge1201.bat"),
        "patch",
        "--in", str(src),
        "--out", str(dst),
        "--bridge-dir", str(bridges),
    ]
    for rule in rules:
        cmd += ["--rules", str(rule)]
    run(cmd, dict(os.environ, JAVA_HOME=java_home))


def extract_nested(outer, dst):
    with zipfile.ZipFile(outer) as zin:
        dst.write_bytes(zin.read(NESTED))
    return dst


def replace_in_zip(src, dst, replacements):
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename in replacements:
                continue
            zout.writestr(item, zin.read(item.filename))
        for name, path in replacements.items():
            zout.write(path, name)


def replace_nested(outer_src, outer_dst, nested_src):
    with zipfile.ZipFile(outer_src) as zin, zipfile.ZipFile(outer_dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == NESTED:
                continue
            zout.writestr(item, zin.read(item.filename))
        zout.write(nested_src, NESTED)


def compile_rl(source_dir, rl_jar, stub, fabric_api, loader, netty, out_dir, java_home):
    javac = Path(java_home) / "bin" / "javac.exe"
    if not javac.exists():
        javac = Path(java_home) / "bin" / "javac"
    client_net = out_dir / "fabric-networking-client.jar"
    with zipfile.ZipFile(fabric_api) as z:
        name = "META-INF/jars/fabric-networking-api-v1-0.102.0.jar"
        client_net.write_bytes(z.read(name))
    cp = os.pathsep.join(str(p) for p in [stub, rl_jar, client_net, loader, *netty])
    sources = sorted(str(p) for p in (source_dir / RL_PACKAGE).glob("*.java"))
    run([str(javac), "--release", "17", "-nowarn", "-proc:none", "-cp", cp,
         "-d", str(out_dir), *sources], dict(os.environ, JAVA_HOME=java_home))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_bridges(out_dir, netty, java_home):
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, str(ROOT / "tools" / "build_bridges.py"),
        "--stub", str(ROOT / "work" / "cb" / "data" / "jars" / "client-1.21.1-intermediary.jar"),
        "--lib", str(ROOT / "work" / "lib" / "gson-2.11.0.jar"),
        "--lib", str(ROOT / "work" / "instances" / "fabric-1.21.1-server" / "libraries" / "com" / "mojang" / "datafixerupper" / "8.0.16" / "datafixerupper-8.0.16.jar"),
        "--lib", str(ROOT / "work" / "instances" / "fabric-1.21.1-server" / ".fabric" / "processedMods" / "fabric-networking-api-v1-4.2.2+60c3209b6a-cc18a5110f61c2c0.jar"),
        "--lib", netty[0],
        "--lib", netty[1],
        "--lib", str(ROOT / "work" / "corpus" / "deps" / "balm-fabric-1.21.1-21.0.66.jar"),
        "--out", str(out_dir),
    ]
    run(cmd, dict(os.environ, JAVA_HOME=java_home))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(ROOT / "work" / "client" / "ironchests-modelbridge2.jar"))
    ap.add_argument("--out", default=str(ROOT / "work" / "client" / "ironchests-rebuilt.jar"))
    ap.add_argument("--bridges", default=str(ROOT / "work" / "bridges"))
    ap.add_argument("--rl-source", default=str(ROOT / "java" / "src" / "nested" / "java"))
    ap.add_argument("--stub", default=str(ROOT / "work" / "cb" / "data" / "jars" / "client-1.21.1-intermediary.jar"))
    ap.add_argument("--fabric-api", required=True)
    ap.add_argument("--loader", default=str(ROOT / "work" / "target" / "fabric-loader-0.19.5.jar"))
    ap.add_argument("--netty", action="append", default=None,
                    help="netty-buffer / netty-common jars (repeatable)")
    ap.add_argument("--java-home", default=os.environ.get("JAVA_HOME"))
    ap.add_argument("--skip-bridges", action="store_true",
                    help="reuse the existing bridge classes instead of recompiling them")
    args = ap.parse_args()

    java_home = args.java_home
    if not java_home:
        sys.exit("JAVA_HOME is not set (or pass --java-home)")
    input_jar = Path(args.input)
    if not input_jar.exists():
        sys.exit(f"input jar not found: {input_jar}")

    tmp = ROOT / "work" / "tmp" / "rebuild-ironchests"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)

    netty = args.netty or [
        str(ROOT / "work" / "instances" / "fabric-1.21.1-server" / "libraries" / "io" / "netty" / "netty-buffer" / "4.1.97.Final" / "netty-buffer-4.1.97.Final.jar"),
        str(ROOT / "work" / "instances" / "fabric-1.21.1-server" / "libraries" / "io" / "netty" / "netty-common" / "4.1.97.Final" / "netty-common-4.1.97.Final.jar"),
    ]

    if not args.skip_bridges:
        build_bridges(Path(args.bridges), netty, java_home)

    nbt_jar = tmp / "nbt.jar"
    patch(input_jar, nbt_jar,
          [RULES / "ironchests-nbt.json", RULES / "nbt-packet.json"],
          args.bridges, java_home)

    original_rl = tmp / "resourcefullib-original.jar"
    extract_nested(nbt_jar, original_rl)
    rl_classes = tmp / "rl-classes"
    rl_classes.mkdir()
    compile_rl(Path(args.rl_source), original_rl, Path(args.stub), Path(args.fabric_api),
               Path(args.loader), netty, rl_classes, java_home)
    replacements = {RL_PACKAGE + name: rl_classes / RL_PACKAGE / name for name in RL_CLASSES}
    patched_rl = tmp / "resourcefullib-patched.jar"
    replace_in_zip(original_rl, patched_rl, replacements)
    rl_fixed = tmp / "rlfixed.jar"
    replace_nested(nbt_jar, rl_fixed, patched_rl)

    patch(rl_fixed, Path(args.out),
          [RULES / "ironchests-screen.json", RULES / "ironchests-draw.json"],
          args.bridges, java_home)
    print("sha256", sha256(args.out))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
