"""Compile the Java-source bridges against the intermediary stub.

Usage:
  python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar \
      --lib work/lib/gson-2.11.0.jar --out work/bridges

The generated classes are embedded by `mcbridge1201 patch --bridge-dir <out>`.
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stub", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "bridges"))
    ap.add_argument("--lib", action="append", default=[])
    args = ap.parse_args()

    java_home = os.environ.get("JAVA_HOME")
    if not java_home:
        print("JAVA_HOME is required", file=sys.stderr)
        return 2
    javac = os.path.join(java_home, "bin", "javac.exe" if os.name == "nt" else "javac")
    src_root = os.path.join(ROOT, "java", "src", "bridge", "java")
    sources = []
    for dirpath, _, files in os.walk(src_root):
        for f in files:
            if f.endswith(".java"):
                sources.append(os.path.join(dirpath, f))
    if not sources:
        print("no bridge sources under", src_root, file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)
    cp = os.pathsep.join([os.path.abspath(args.stub)] + [os.path.abspath(x) for x in args.lib])
    cmd = [javac, "-nowarn", "-proc:none", "-encoding", "UTF-8", "-cp", cp, "-d", args.out] + sources
    print(" ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        return rc
    print("compiled", len(sources), "bridge source(s) ->", args.out)

    shim_root = os.path.join(ROOT, "java", "src", "bridge-shim", "java")
    shim_sources = []
    for dirpath, _, files in os.walk(shim_root):
        for f in files:
            if f.endswith(".java"):
                shim_sources.append(os.path.join(dirpath, f))
    if shim_sources:
        shim_out = os.path.join(ROOT, "work", "tmp", "bridges-shim")
        os.makedirs(shim_out, exist_ok=True)
        shim_cmd = [javac, "-nowarn", "-proc:none", "-encoding", "UTF-8",
                    "-cp", cp, "-d", shim_out] + shim_sources
        rc = subprocess.call(shim_cmd)
        if rc != 0:
            return rc
        shims = [
            ("net", "fabricmc", "fabric", "api", "client", "networking", "v1",
             "ClientPlayNetworking$PlayChannelHandler.class"),
            ("net", "fabricmc", "fabric", "api", "networking", "v1",
             "ServerPlayNetworking$PlayChannelHandler.class"),
        ]
        for parts in shims:
            nested = os.path.join(shim_out, *parts)
            if not os.path.exists(nested):
                print("shim did not produce", nested, file=sys.stderr)
                return 3
            dest_dir = os.path.join(args.out, *parts[:-1])
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, parts[-1])
            with open(nested, "rb") as src, open(dest, "wb") as dst:
                dst.write(src.read())
            print("embedded legacy shim ->", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
