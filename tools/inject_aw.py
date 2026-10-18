"""Inject an access widener into a mod jar (local build step for the P2 patch pipeline).

Why: 1.21.1 made several constructors/members private (e.g. Identifier(String,String)).
Widening access is simpler and more faithful than rewriting each call site, and it covers
call sites that our conservative bytecode matcher skips (arguments computed by calls).

Usage:
  python tools/inject_aw.py --jar in.jar --out out.jar --aw rules/fabric-1.21.1/mcbridge.accesswidener
"""
from __future__ import annotations

import argparse
import json
import os
import zipfile


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--aw", required=True)
    ap.add_argument("--entry", default="mcbridge.accesswidener")
    args = ap.parse_args()

    aw_text = open(args.aw, encoding="utf-8").read()
    with zipfile.ZipFile(args.jar) as zin:
        entries = {n: zin.read(n) for n in zin.namelist() if not n.endswith("/")}

    meta_name = "fabric.mod.json"
    if meta_name not in entries:
        print("not a fabric mod jar", flush=True)
        return 2
    meta = json.loads(entries[meta_name].decode("utf-8"))
    meta["accessWidener"] = args.entry
    entries[meta_name] = json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8")
    entries[args.entry] = aw_text.encode("utf-8")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in entries.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(info, data)
    print(f"injected {args.entry} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
