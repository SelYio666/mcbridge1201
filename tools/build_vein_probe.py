#!/usr/bin/env python3
"""Build the p255 vein-bridge probe mod (jar stays in work/, never committed).

    python tools/build_vein_probe.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar \
        --lib work/target/fabric-loader-0.19.5.jar \
        --lib work/instances/fabric-1.21.1-server/.fabric/processedMods/fabric-command-api-v2-2.2.28+6ced4dd96a-7a2cb885ceec980f.jar \
        --bridge-classes work/targets/fabric-1.21.1/bridges \
        --out work/shim/mcbridge-vein-probe-1.0.0.jar

The probe references the compiled bridge classes (they load from the patched VeinMiner jar
at runtime); --bridge-classes puts them on the compile classpath only.
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the p255 vein bridge probe mod")
    ap.add_argument("--stub", required=True, help="1.21.1 intermediary client jar (compile stub)")
    ap.add_argument("--lib", action="append", default=[], help="compile dependency (repeatable)")
    ap.add_argument("--bridge-classes", required=True,
                    help="compiled bridge classes dir (compile-time only; runtime loads them from the patched mod)")
    ap.add_argument("--out", required=True, help="output jar path")
    ap.add_argument("--src", default=os.path.join("probes", "p255-vein-bridge", "src"),
                    help="probe source root")
    args = ap.parse_args(argv)

    java_home = os.environ.get("JAVA_HOME")
    if not java_home:
        print("JAVA_HOME is not set", file=sys.stderr)
        return 2
    javac = os.path.join(java_home, "bin", "javac.exe")
    if not os.path.exists(javac):
        javac = os.path.join(java_home, "bin", "javac")

    java_src = os.path.join(args.src, "java")
    resources = os.path.join(args.src, "resources")
    sources = []
    for root, _dirs, files in os.walk(java_src):
        for name in files:
            if name.endswith(".java"):
                sources.append(os.path.join(root, name))
    if not sources:
        print("no sources under", java_src, file=sys.stderr)
        return 2
    if not os.path.exists(os.path.join(resources, "fabric.mod.json")):
        print("missing fabric.mod.json", file=sys.stderr)
        return 2

    build_dir = os.path.join("work", "tmp", "vein-probe-build")
    shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(build_dir, exist_ok=True)
    classpath = os.pathsep.join([args.stub, args.bridge_classes] + args.lib)
    cmd = [javac, "-nowarn", "-proc:none", "-encoding", "UTF-8", "-cp", classpath, "-d", build_dir] + sources
    print(" ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        return rc
    shutil.copyfile(os.path.join(resources, "fabric.mod.json"), os.path.join(build_dir, "fabric.mod.json"))

    out_parent = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_parent, exist_ok=True)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(build_dir):
            for name in sorted(files):
                full = os.path.join(root, name)
                info = zipfile.ZipInfo(os.path.relpath(full, build_dir).replace(os.sep, "/"),
                                       date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o644 << 16
                zf.writestr(info, open(full, "rb").read(), zipfile.ZIP_DEFLATED)
    print("built", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
