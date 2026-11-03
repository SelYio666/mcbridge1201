#!/usr/bin/env python3
"""Conversion cache key + stale-bridge guard.

A converted jar is only valid for the exact inputs that produced it. This tool names those
inputs, hashes them into one key, and can say *which* input moved when a key stops matching -
"cache miss" alone is useless when the reason is a rebuilt bridge rather than a new source jar.

    # compute the key (prints it; --json writes the components too)
    python tools/conversion_cache.py key --profile targets/fabric-1.21.1.json \
        --source work/corpus/ironchests-5.0.2-fabric.jar --bridge-dir work/targets/fabric-1.21.1/bridges

    # record a finished conversion
    python tools/conversion_cache.py store --profile ... --source ... --bridge-dir ... \
        --artifact work/client/ironchests-1.21.1.jar

    # check one before rebuilding
    python tools/conversion_cache.py lookup --profile ... --source ... --bridge-dir ...

The key covers: bridge ABI, the target profile (path + hash + identity fields), the source jar
bytes, every pinned index in the profile, the ordered rule package, the compiled bridge classes,
the engine commit and any extra patch configuration the caller adds.

`lookup` never says "hit" for a conversion whose bridge came from another ABI or another target:
that is the stale-bridge case this exists to catch, and it is reported as a component diff.

Exit codes: 0 hit / key printed, 1 miss (lookup only), 2 usage or missing input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIDGE_ABI = "mcbridge-bridge-1"
PROFILE_SCHEMA = "target-profile-1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def resolve(path: str) -> Path:
    p = Path(path.replace("\\", "/"))
    return p if p.is_absolute() else ROOT / p


def load_profile(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != PROFILE_SCHEMA:
        sys.exit(f"{path}: unsupported schemaVersion {data.get('schemaVersion')!r}")
    pipeline = data.get("pipeline") or {}
    if pipeline.get("bridgeAbi") != BRIDGE_ABI:
        sys.exit(f"{path}: bridge ABI {pipeline.get('bridgeAbi')!r} != {BRIDGE_ABI!r}; every cached"
                 " conversion for the old ABI is stale by definition")
    return data


def bridge_dir_hash(bridge_dir: Path | None) -> dict:
    if bridge_dir is None:
        return {"present": False}
    if not bridge_dir.is_dir():
        sys.exit(f"bridge dir missing: {bridge_dir}")
    entries = []
    for p in sorted(bridge_dir.rglob("*.class"), key=lambda x: x.relative_to(bridge_dir).as_posix()):
        entries.append({"class": p.relative_to(bridge_dir).as_posix(), "sha256": sha256_file(p)})
    h = hashlib.sha256()
    for e in entries:
        h.update(e["class"].encode("utf-8"))
        h.update(e["sha256"].encode("ascii"))
    return {"present": True, "count": len(entries), "sha256": h.hexdigest()}


def rules_component(profile: dict, rules: list[str], use_profile_order: bool) -> dict:
    refs = list(profile.get("pipeline", {}).get("ruleOrder") or []) if use_profile_order else rules
    if not refs:
        sys.exit("no rules: pass --rules ... or --rules-from-profile")
    entries = []
    for ref in refs:
        p = resolve(ref)
        if not p.is_file():
            sys.exit(f"rule file missing: {p}")
        entries.append({"file": Path(ref).name, "sha256": sha256_file(p)})
    h = hashlib.sha256()
    for e in entries:
        h.update(e["file"].encode("utf-8"))
        h.update(e["sha256"].encode("ascii"))
    return {"frozenOrder": use_profile_order, "count": len(entries),
            "sha256": h.hexdigest(), "files": entries}


def index_components(profile: dict) -> dict:
    indices = profile.get("indices") or {}
    out = {}
    order = ["bridgeStub", "clientJar", "mappings", "loader"]
    for key in order:
        entry = indices.get(key)
        if entry:
            out[key] = entry.get("sha256")
    for i, entry in enumerate(indices.get("api") or []):
        out[f"api[{i}]"] = entry.get("sha256")
    for i, entry in enumerate(indices.get("libs") or []):
        out[f"libs[{i}]"] = entry.get("sha256")
    return out


def components(args) -> dict:
    profile_path = resolve(args.profile)
    profile = load_profile(profile_path)
    target = profile.get("target") or {}
    source = None
    if args.source:
        sp = resolve(args.source)
        if not sp.is_file():
            sys.exit(f"source jar missing: {sp}")
        source = {"sha256": sha256_file(sp), "size": sp.stat().st_size}
    config = {}
    for item in args.config or []:
        if "=" not in item:
            sys.exit(f"--config expects key=value, got {item!r}")
        k, v = item.split("=", 1)
        config[k] = v
    return {
        "bridgeAbi": BRIDGE_ABI,
        "profile": {
            "path": profile_path.relative_to(ROOT).as_posix() if profile_path.is_relative_to(ROOT)
                    else str(profile_path),
            "sha256": sha256_file(profile_path),
            "profileId": profile.get("profileId"),
            "targetId": target.get("id"),
            "minecraft": target.get("minecraft"),
            "loader": target.get("loader"),
            "javaMajor": target.get("javaMajor"),
            "classMajorMax": target.get("classMajorMax"),
            "namespace": target.get("namespace"),
        },
        "engine": (profile.get("pipeline") or {}).get("engine") or {},
        "source": source,
        "indices": index_components(profile),
        "rules": rules_component(profile, args.rules or [], args.rules_from_profile),
        "bridges": bridge_dir_hash(resolve(args.bridge_dir) if args.bridge_dir else None),
        "config": config,
    }


def key_of(comp: dict) -> str:
    return hashlib.sha256(canonical(comp).encode("utf-8")).hexdigest()


def cache_dir_for(args, profile: dict) -> Path:
    if args.cache_dir:
        return resolve(args.cache_dir)
    cdir = (profile.get("pipeline", {}).get("output") or {}).get("cache") or "work/cache"
    return resolve(cdir)


def diff_components(old: dict, new: dict) -> list[str]:
    """Report which components moved, so a miss has a cause instead of a shrug."""
    out = []

    def walk(a, b, prefix):
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(set(a) | set(b)):
                walk(a.get(k), b.get(k), f"{prefix}.{k}" if prefix else k)
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                out.append(f"{prefix}: {len(a)} -> {len(b)} entries")
                return
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{prefix}[{i}]")
        elif a != b:
            sa = str(a)
            sb = str(b)
            out.append(f"{prefix}: {sa[:20]} -> {sb[:20]}")

    walk(old, new, "")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--profile", required=True)
        p.add_argument("--source", default=None, help="the immutable original (or intermediate) jar")
        p.add_argument("--bridge-dir", default=None, help="compiled bridge classes embedded by patch")
        p.add_argument("--rules", action="append", default=[], help="rule file (repeatable)")
        p.add_argument("--rules-from-profile", action="store_true",
                       help="use pipeline.ruleOrder as the authoritative list")
        p.add_argument("--config", action="append", default=[], help="extra patch option key=value")
        p.add_argument("--cache-dir", default=None)

    k = sub.add_parser("key", help="print the conversion cache key")
    common(k)
    k.add_argument("--json", default=None)

    s = sub.add_parser("store", help="record a finished conversion under its key")
    common(s)
    s.add_argument("--artifact", required=True, help="the converted jar")
    s.add_argument("--out-json", default=None)

    lk = sub.add_parser("lookup", help="check whether this exact conversion was already produced")
    common(lk)
    lk.add_argument("--json", default=None)

    args = ap.parse_args()
    comp = components(args)
    key = key_of(comp)
    profile = load_profile(resolve(args.profile))
    cdir = cache_dir_for(args, profile)
    record_path = cdir / f"{key}.json"

    if args.cmd == "key":
        print(key)
        if args.json:
            Path(args.json).write_text(
                json.dumps({"key": key, "components": comp}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8", newline="\n")
        return 0

    if args.cmd == "store":
        art = resolve(args.artifact)
        if not art.is_file():
            sys.exit(f"artifact missing: {art}")
        cdir.mkdir(parents=True, exist_ok=True)
        record = {"key": key, "components": comp,
                  "artifact": {"sha256": sha256_file(art), "size": art.stat().st_size}}
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8", newline="\n")
        print(f"stored {record_path.relative_to(ROOT).as_posix()}")
        if args.out_json:
            Path(args.out_json).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8", newline="\n")
        return 0

    # lookup
    hit = record_path.is_file()
    report = {"key": key, "hit": hit, "record": str(record_path), "cacheDir": str(cdir)}
    if hit:
        report["artifact"] = json.loads(record_path.read_text(encoding="utf-8")).get("artifact")
        print(f"HIT {key}")
    else:
        stale = sorted(cdir.glob("*.json")) if cdir.is_dir() else []
        reasons = []
        same_source = None
        if same_source is None:
            for path in stale:
                try:
                    rec = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                if (rec.get("components", {}).get("source") or {}).get("sha256") == (
                        comp.get("source") or {}).get("sha256"):
                    same_source = rec
                    break
        if same_source:
            reasons = diff_components(same_source["components"], comp)
            report["comparedWith"] = same_source.get("key")
        report["reasons"] = reasons
        print(f"MISS {key}")
        if same_source:
            print(f"  closest cached conversion for the same source: {same_source.get('key')}")
            for r in reasons:
                print(f"  changed: {r}")
        else:
            print("  no cached conversion for this source jar")
    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8", newline="\n")
    return 0 if hit else 1


if __name__ == "__main__":
    raise SystemExit(main())
