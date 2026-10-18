"""Pre-remap a Fabric server's game jar with the local body-preserving remapper.

Why this exists: on hosts where `Files.isWritable` is false (restricted token), Fabric
Loader's zipfs-based remap refuses to write, so the loader can never produce
`.fabric/remappedJars/.../server-intermediary.jar`. This script produces the same jar
with our ASM remapper; the loader then sees the file and skips its own remap.

Usage:
  python tools/remap_server.py --instance work/instances/fabric-1.21.1-server \
      --loader 0.19.5 --mappings work/cb/data/mappings/intermediary-1.21.1.tiny
"""
import argparse
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "java", "build", "install", "mcbridge1201", "bin",
                   "mcbridge1201.bat" if os.name == "nt" else "mcbridge1201")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True)
    ap.add_argument("--loader", required=True)
    ap.add_argument("--mappings", required=True)
    ap.add_argument("--minecraft", default="1.21.1")
    args = ap.parse_args()

    inst = os.path.abspath(args.instance)
    src = os.path.join(inst, "versions", args.minecraft, f"server-{args.minecraft}.jar")
    if not os.path.exists(src):
        print(f"server jar not found: {src}", file=sys.stderr)
        return 2
    out_dir = os.path.join(inst, ".fabric", "remappedJars",
                           f"minecraft-{args.minecraft}-{args.loader}")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "server-intermediary.jar")
    if not os.path.exists(CLI):
        print(f"CLI not built: {CLI} (run gradle installDist in java/)", file=sys.stderr)
        return 2
    env = dict(os.environ)
    if not env.get("JAVA_HOME"):
        print("JAVA_HOME is required", file=sys.stderr)
        return 2
    subprocess.run([CLI, "remap-jar", "--in", src, "--out", out, "--mappings",
                    os.path.abspath(args.mappings)], check=True, env=env)
    stale = out + ".tmp"
    if os.path.exists(stale):
        os.remove(stale)
    print(f"installed {out} sha256={sha256(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
