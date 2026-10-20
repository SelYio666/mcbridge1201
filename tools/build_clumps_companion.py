#!/usr/bin/env python3
"""Builds the companion jar that restores Clumps' experience-orb merging.

The converted Clumps jar lost its MixinExperienceOrb (load-bearing), so this companion does the
merging on the server tick instead. It is compiled against the 1.21.1 intermediary stub and the
Fabric API/lifecycle jars, then packaged with its fabric.mod.json. No game or mod jar is shipped by
this repository; only this source and script are.
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the Clumps merge companion mod")
    ap.add_argument("--stub", required=True, help="1.21.1 intermediary client jar (compile stub)")
    ap.add_argument("--lib", action="append", default=[], help="extra compile dependency (repeatable)")
    ap.add_argument("--out", required=True, help="output jar path")
    ap.add_argument("--src", default=os.path.join("java", "src", "compat-clumps"),
                    help="companion source root")
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
    mod_json = os.path.join(resources, "fabric.mod.json")
    if not os.path.exists(mod_json):
        print("missing", mod_json, file=sys.stderr)
        return 2

    build_dir = os.path.join("work", "tmp", "compat-clumps-build")
    shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(build_dir, exist_ok=True)
    classpath = os.pathsep.join([args.stub] + args.lib)
    cmd = [javac, "-nowarn", "-proc:none", "-encoding", "UTF-8", "-cp", classpath, "-d", build_dir] + sources
    print(" ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        return rc
    shutil.copyfile(mod_json, os.path.join(build_dir, "fabric.mod.json"))

    out_parent = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_parent, exist_ok=True)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(build_dir):
            for name in files:
                full = os.path.join(root, name)
                zf.write(full, os.path.relpath(full, build_dir).replace(os.sep, "/"))
    print("built", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
