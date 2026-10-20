#!/usr/bin/env python3
"""Checks that every patched jar carries the same bridge classes as the canonical bridge dir.

Each patched jar embeds its own copy of the bridge classes, and the first copy loaded by Fabric
wins. A stale copy silently shadows the new one (observed: an old AppleSkin jar without
FabricLegacyNetworking.sendPacket broke ShulkerBoxTooltip's handshake). This script hashes every
embedded bridge class and fails when a jar differs from the canonical bridge directory or when two
jars disagree with each other.
"""
import argparse
import hashlib
import os
import sys
import zipfile

BRIDGE_PREFIX = "top/mcbridge1201/bridge/"
SHIM_SUFFIX = "/ClientPlayNetworking$PlayChannelHandler.class"


def canonical_classes(bridge_dir):
    found = {}
    for root, _dirs, files in os.walk(bridge_dir):
        for name in files:
            if not name.endswith(".class"):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, bridge_dir).replace(os.sep, "/")
            with open(full, "rb") as f:
                found[rel] = hashlib.sha256(f.read()).hexdigest()
    return found


def jar_classes(path):
    found = {}
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if not name.endswith(".class"):
                continue
            if name.startswith(BRIDGE_PREFIX) or name.endswith(SHIM_SUFFIX):
                found[name] = hashlib.sha256(zf.read(name)).hexdigest()
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check embedded bridge class consistency")
    ap.add_argument("--bridge-dir", required=True, help="canonical bridge output directory")
    ap.add_argument("--jar", action="append", default=[], help="patched jar (repeatable)")
    args = ap.parse_args(argv)
    if not args.jar:
        print("no --jar given", file=sys.stderr)
        return 2
    canonical = canonical_classes(args.bridge_dir)
    if not canonical:
        print("no classes under", args.bridge_dir, file=sys.stderr)
        return 2

    jars = {path: jar_classes(path) for path in args.jar}
    problems = 0
    print("canonical bridge classes:", len(canonical))
    for name in sorted(canonical):
        expected = canonical[name]
        owners = [path for path, classes in jars.items() if name in classes]
        bad = [path for path in owners if jars[path][name] != expected]
        if bad:
            problems += len(bad)
            print(f"MISMATCH {name}")
            for path in bad:
                print(f"  {os.path.basename(path)}: {jars[path][name][:16]} != {expected[:16]}")
    # cross-jar disagreements for classes absent from the canonical dir
    seen = {}
    for path, classes in jars.items():
        for name, digest in classes.items():
            if name in canonical:
                continue
            seen.setdefault(name, {}).setdefault(digest, []).append(os.path.basename(path))
    for name in sorted(seen):
        if len(seen[name]) > 1:
            problems += 1
            print(f"CROSS-JAR MISMATCH {name}")
            for digest, owners in seen[name].items():
                print(f"  {digest[:16]}: {', '.join(owners)}")

    print("checked", len(jars), "jar(s); problems =", problems)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
