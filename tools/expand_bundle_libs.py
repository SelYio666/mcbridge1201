#!/usr/bin/env python3
"""Expand a Fabric API bundle into its module jars and add them to the target closure.

The bundle jar keeps its modules under META-INF/jars/, so javac never sees them on a classpath.
A server instance normally expands them at first launch; for compilation we do it here, without
running the game, and record every module's sha256 in the same lock the MC libraries live in.

    python tools/expand_bundle_libs.py
    python tools/expand_bundle_libs.py --bundle work/target/fabric-api-0.119.4+1.21.4.jar

Exit codes: 0 expanded, 2 missing input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUNDLE = ROOT / "work" / "target" / "fabric-api-0.119.4+1.21.4.jar"
LOCK = ROOT / "manifests" / "target-fabric-1.21.4-libs.lock.json"
OUT = ROOT / "work" / "target" / "api-modules-1214"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundle", default=str(DEFAULT_BUNDLE))
    args = ap.parse_args()
    bundle = Path(args.bundle)
    if not bundle.is_file():
        print(f"missing bundle: {bundle}", file=sys.stderr)
        return 2
    if not LOCK.is_file():
        print(f"missing closure lock: {LOCK}", file=sys.stderr)
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    known = {e["path"] for e in lock["libraries"]}
    added = []
    with zipfile.ZipFile(bundle) as z:
        for name in z.namelist():
            if not (name.startswith("META-INF/jars/") and name.endswith(".jar")):
                continue
            data = z.read(name)
            dst = OUT / Path(name).name
            if not dst.is_file() or sha256_file(dst) != hashlib.sha256(data).hexdigest():
                dst.write_bytes(data)
            rel = dst.relative_to(ROOT).as_posix()
            entry = {
                "name": f"fabric-api module {Path(name).stem}",
                "path": rel,
                "size": dst.stat().st_size,
                "sha256": sha256_file(dst),
                "sha1Ok": None,
                "role": "fabric api module (expanded from the bundle)",
            }
            if rel not in known:
                lock["libraries"].append(entry)
                lock["classpath"].append(rel)
                added.append(rel)

    lock["count"] = len(lock["libraries"])
    lock["totalBytes"] = sum(e["size"] for e in lock["libraries"])
    lock.setdefault("expansions", []).append({
        "bundle": bundle.relative_to(ROOT).as_posix(),
        "modules": len([e for e in lock["libraries"] if e.get("role", "").startswith("fabric api module")]),
        "note": "The bundle keeps modules under META-INF/jars/; they are expanded here so javac and"
                " any later run see the same jars.",
    })
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"expanded {len(added)} module(s) into {OUT.relative_to(ROOT).as_posix()}")
    print(f"closure now {lock['count']} jar(s), {lock['totalBytes'] / 1048576:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
