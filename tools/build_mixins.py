"""Compile the Java-source mixin ports against the 1.21.1 server intermediary jar.

Usage:
  python tools/build_mixins.py --stub work/remap/server-intermediary.jar \
      --lib work/instances/.../sponge-mixin-0.17.4+mixin.0.8.7.jar \
      --lib work/bridges --out work/mixins

The mixin sources use @Shadow/@Overwrite, so they must be compiled against the server jar
(the client jar does not contain ServerChunkManager) and the Sponge Mixin library. The
annotation processor is disabled; it is not needed and would require a full ASM classpath.
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stub", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "mixins"))
    ap.add_argument("--lib", action="append", default=[])
    ap.add_argument("--src", default=os.path.join(ROOT, "java", "src", "mixin", "java"))
    args = ap.parse_args()

    java_home = os.environ.get("JAVA_HOME")
    if not java_home:
        print("JAVA_HOME is required", file=sys.stderr)
        return 2
    javac = os.path.join(java_home, "bin", "javac.exe" if os.name == "nt" else "javac")
    sources = []
    for dirpath, _, files in os.walk(args.src):
        for f in files:
            if f.endswith(".java"):
                sources.append(os.path.join(dirpath, f))
    if not sources:
        print("no mixin sources under", args.src, file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)
    cp = os.pathsep.join([os.path.abspath(args.stub)] + [os.path.abspath(x) for x in args.lib])
    cmd = [javac, "-proc:none", "-nowarn", "-encoding", "UTF-8", "-cp", cp, "-d", args.out] + sources
    print(" ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        return rc
    print("compiled", len(sources), "mixin source(s) ->", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
