#!/usr/bin/env python3
"""Reachability canary for the download sources (metadata + a few representative files).

This deliberately does NOT download whole files: it checks that the official endpoints and the
verified mirrors answer for a representative path, and records expected misses (Fabric API has
no BMCL mirror). Full integrity is covered by the full-install runs (runs/p118 for 1.21.1 and
runs/p122 for 1.20.1), not by this script.

By default only the core official endpoints (vanilla / Fabric / Forge) gate the exit code;
mirror and NeoForge failures are reported as health information because those hosts fluctuate.
Pass --strict to make mirrors and NeoForge gating as well.

Usage:
  python tools/check_download_sources.py [--strict]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402

OUT = ROOT / "runs" / "p122-source-canary"
UA = {"User-Agent": "mcbridge-canary/0.1"}


def probe(url: str, timeout: int = 20, allow_404: bool = False) -> dict:
    t0 = time.time()
    rec = {"url": url, "expect_404": allow_404}
    try:
        req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            rec.update(status=r.status, final=r.geturl(),
                       content_length=r.headers.get("Content-Length"),
                       content_range=r.headers.get("Content-Range"),
                       ms=round((time.time() - t0) * 1000))
            rec["ok"] = r.status in (200, 206) or (allow_404 and r.status == 404)
    except urllib.error.HTTPError as exc:
        rec.update(status=exc.code, ms=round((time.time() - t0) * 1000))
        rec["ok"] = allow_404 and exc.code == 404
    except Exception as exc:  # noqa: BLE001 - network canary
        rec.update(error=repr(exc), ms=round((time.time() - t0) * 1000), ok=False)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="also fail when verified mirrors or NeoForge endpoints are unreachable")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = mclaunch.http_json(mclaunch.MANIFEST_URL, max_age=0)
    v = next(x for x in manifest["versions"] if x["id"] == "1.21.1")
    meta = mclaunch.http_json(v["url"], max_age=0)
    client = meta["downloads"]["client"]
    idx_url = meta["assetIndex"]["url"]
    idx = mclaunch.http_json(idx_url, max_age=0)
    first_obj = next(iter(idx["objects"].values()))
    asset_url = f"{mclaunch.ASSET_BASE}/{first_obj['hash'][:2]}/{first_obj['hash']}"

    loader = ("https://maven.fabricmc.net/net/fabricmc/fabric-loader/0.19.5/"
              "fabric-loader-0.19.5.jar")
    api = ("https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/"
           "0.102.0+1.21.1/fabric-api-0.102.0+1.21.1.jar")
    inter = ("https://maven.fabricmc.net/net/fabricmc/intermediary/1.21.1/"
             "intermediary-1.21.1.jar")
    lib = "https://libraries.minecraft.net/com/github/oshi/oshi-core/6.4.10/oshi-core-6.4.10.jar"
    forge = ("https://maven.minecraftforge.net/net/minecraftforge/forge/1.20.1-47.4.10/"
             "forge-1.20.1-47.4.10-installer.jar")
    neo = ("https://maven.neoforged.net/releases/net/neoforged/neoforge/21.1.264/"
           "neoforge-21.1.264-installer.jar")

    required = [
        ("mojang manifest", mclaunch.MANIFEST_URL),
        ("mojang version json", v["url"]),
        ("mojang asset index", idx_url),
        ("client jar", client["url"]),
        ("library", lib),
        ("asset object", asset_url),
        ("fabric loader list", "https://meta.fabricmc.net/v2/versions/loader/1.21.1"),
        ("fabric loader jar", loader),
        ("fabric api jar", api),
        ("fabric intermediary jar", inter),
        ("forge promos", mclaunch.FORGE_PROMOS),
        ("forge installer", forge),
    ]
    # Separate bucket: the NeoForge host is independently flaky; its failure should be
    # reported but must not mark the vanilla/Fabric/Forge chain as broken.
    neoforge = [
        ("neoforge versions", mclaunch.NEOFORGE_VERSIONS),
        ("neoforge installer", neo),
    ]
    expected_miss = [
        ("bmcl fabric-api", "https://bmclapi2.bangbang93.com/maven/net/fabricmc/fabric-api/fabric-api/0.102.0+1.21.1/fabric-api-0.102.0+1.21.1.jar"),
        ("bmcl forge promos", "https://bmclapi2.bangbang93.com/forge/promotions_slim.json"),
        ("bmcl neoforge api", "https://bmclapi2.bangbang93.com/neoforge/versions"),
    ]
    # verified mirrors for paths the launcher actually rewrites
    mirrored = []
    for label, url in (("bmcl loader jar", loader), ("bmcl intermediary jar", inter),
                       ("bmcl library", lib), ("bmcl asset", asset_url),
                       ("bmcl manifest", mclaunch.MANIFEST_URL),
                       ("bmcl fabric loader list", "https://meta.fabricmc.net/v2/versions/loader/1.21.1")):
        candidates = mclaunch.mirror_urls(url)[1:]
        for cand in candidates:
            mirrored.append((label, cand))

    results = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "required": [], "mirrors": [],
               "neoforge": [], "expected_misses": []}

    def run_group(items, bucket, allow404):
        with ThreadPoolExecutor(max_workers=6) as pool:
            futs = {pool.submit(probe, url, 20, allow404): label for label, url in items}
            for fut in as_completed(futs):
                label = futs[fut]
                rec = fut.result()
                rec["label"] = label
                results[bucket].append(rec)
        results[bucket].sort(key=lambda r: r["label"])

    run_group(required, "required", False)
    run_group(mirrored, "mirrors", False)
    run_group(neoforge, "neoforge", False)
    run_group(expected_miss, "expected_misses", True)

    core_ok = all(r["ok"] for r in results["required"])
    mirrors_ok = all(r["ok"] for r in results["mirrors"])
    neoforge_ok = all(r["ok"] for r in results["neoforge"])
    results.update(ok=core_ok, mirrors_ok=mirrors_ok, neoforge_ok=neoforge_ok, strict=args.strict)
    ok = core_ok and (not args.strict or (mirrors_ok and neoforge_ok))
    (OUT / "canary.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    for bucket in ("required", "mirrors", "neoforge", "expected_misses"):
        print(f"== {bucket}")
        for r in results[bucket]:
            line = f"  {r['label']:28s} {str(r.get('status')):>4} {r['ms']:>6} ms"
            if r.get("content_length"):
                line += f"  len={r['content_length']}"
            if r.get("error"):
                line += "  ERR " + r["error"][:80]
            print(line)
    print("RESULT:", "OK" if ok else "FAIL",
          f"(core={core_ok}, mirrors={mirrors_ok}, neoforge={neoforge_ok}, strict={args.strict})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
