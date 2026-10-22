#!/usr/bin/env python3
"""Benchmark: per-request urllib vs the pooled transport (launcher/fetch.py).

Downloads the same N asset objects twice (cold connections vs keep-alive) and prints
wall time / throughput. Network variance is reported, not hidden: run it twice.
"""
from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "launcher"))
import fetch  # noqa: E402

UA = {"User-Agent": "mcbridge-bench/1.0"}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 120


def index_objects():
    with urllib.request.urlopen(urllib.request.Request(
            "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json", headers=UA),
            timeout=20) as r:
        import json
        manifest = json.loads(r.read())
    v = next(x for x in manifest["versions"] if x["id"] == "1.21.1")
    with urllib.request.urlopen(urllib.request.Request(v["url"], headers=UA), timeout=20) as r:
        import json
        meta = json.loads(r.read())
    with urllib.request.urlopen(urllib.request.Request(meta["assetIndex"]["url"], headers=UA),
                                timeout=20) as r:
        import json
        idx = json.loads(r.read())
    return [o["hash"] for o in list(idx["objects"].values())[:N]]


def url_of(h):
    return f"https://resources.download.minecraft.net/{h[:2]}/{h}"


def run_urllib(hashes):
    t0 = time.time()
    total = 0
    for h in hashes:
        with urllib.request.urlopen(urllib.request.Request(url_of(h), headers=UA), timeout=30) as r:
            total += len(r.read())
    return time.time() - t0, total


def run_pooled(hashes):
    t0 = time.time()
    total = 0
    for h in hashes:
        total += len(fetch.get_bytes(url_of(h), timeout=30))
    return time.time() - t0, total


hashes = index_objects()
print(f"assets: {len(hashes)}  (1.21.1)")
t, b = run_pooled(hashes[:5])  # warm the pool/DNS before timing
print(f"warmup pooled: {t:.2f}s {b / 1e6:.2f} MB")

t1, b1 = run_urllib(hashes)
t2, b2 = run_pooled(hashes)
for name, t, b in (("urllib (conn per file)", t1, b1), ("pooled (keep-alive+gzip)", t2, b2)):
    print(f"{name:28s} {t:7.2f}s  {b / 1e6:7.2f} MB  {len(hashes) / t:6.1f} req/s")
if t2 > 0:
    print(f"speedup: {t1 / t2:.2f}x")
