#!/usr/bin/env python3
"""Bounded cold/hot download benchmark for the launcher's download path.

A full vanilla install downloads ~3,900 asset objects; doing that twice per version
would take an hour and gigabytes, so this tool measures the representative chain:
client jar + every allowed library + a fixed asset sample (+ Fabric loader install).

Each version is measured twice on the same root: "cold" (empty root) and "hot"
(files already there, only hash checks). The root is deleted afterwards unless
--keep is given; the JSON result is written under runs/p117-download-bench/.

Usage:
  python tools/bench_download.py --mc 1.21.1 --assets 200 --fabric
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402

RUNS = ROOT / "runs" / "p117-download-bench"


def dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def phase(progress: mclaunch.Progress, name: str, start: float, before_seq: int,
          files: int, bytes_done: int) -> dict:
    events = [e for e in mclaunch.DOWNLOAD_EVENTS if e.get("seq", 0) > before_seq]
    return {
        "phase": name,
        "seconds": round(time.time() - start, 3),
        "files": files,
        "bytes": bytes_done,
        "mb_per_s": round((bytes_done / 1048576) / max(0.001, time.time() - start), 3),
        "downloads": len([e for e in events if e.get("error") is None]),
        "failures": len([e for e in events if e.get("error")]),
        "mirrors": len([e for e in events if e.get("mirror")]),
        "retries": sum(max(0, (e.get("attempts") or 1) - 1) for e in events),
        "sources": sorted({(e.get("final") or e.get("url") or "").split("/")[2]
                           for e in events if e.get("final") or e.get("url")}),
    }


def one_pass(mc: str, root: Path, label: str, assets_sample: int) -> dict:
    mclaunch._JSON_CACHE.clear()
    mclaunch._SIDECAR_CACHE.clear()
    result = {"label": label, "mc": mc, "phases": []}
    v = mclaunch.find_version(mc)
    meta = mclaunch.http_json(v["url"], max_age=0)
    vdir = root / "versions" / mc
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / f"{mc}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # 1) client jar
    progress = mclaunch.Progress()
    before = mclaunch._DOWNLOAD_SEQ
    start = time.time()
    jar = meta["downloads"]["client"]
    mclaunch.download(jar["url"], vdir / f"{mc}.jar", jar.get("sha1"), progress=progress)
    result["phases"].append(phase(progress, "client_jar", start, before, 1,
                                  progress.snapshot()["bytes_done"]))

    # 2) every allowed library (same filter and concurrency as install_vanilla)
    libs = [lib for lib in meta.get("libraries", []) if mclaunch.allowed_win(lib)]
    progress = mclaunch.Progress()
    progress.set(total=len(libs), done=0)
    before = mclaunch._DOWNLOAD_SEQ
    start = time.time()

    def get_lib(lib):
        art = (lib.get("downloads") or {}).get("artifact")
        if art:
            mclaunch.download(art["url"], root / "libraries" / art["path"],
                              art.get("sha1"), progress=progress)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(get_lib, lib) for lib in libs]
        for f in as_completed(futs):
            f.result()
            progress.inc()
    result["phases"].append(phase(progress, "libraries", start, before, len(libs),
                                  progress.snapshot()["bytes_done"]))

    # 3) a fixed asset sample (first N objects by name)
    idx = meta.get("assetIndex")
    if idx:
        idx_path = root / "assets" / "indexes" / f"{idx['id']}.json"
        mclaunch.download(idx["url"], idx_path, idx.get("sha1"))
        index = json.loads(idx_path.read_text(encoding="utf-8"))
        objects = sorted(index.get("objects", {}).items())[:assets_sample]
        progress = mclaunch.Progress()
        progress.set(total=len(objects), done=0)
        before = mclaunch._DOWNLOAD_SEQ
        start = time.time()

        def get_obj(item):
            _name, obj = item
            dest = root / "assets" / "objects" / obj["hash"][:2] / obj["hash"]
            mclaunch.download(f"{mclaunch.ASSET_BASE}/{obj['hash'][:2]}/{obj['hash']}",
                              dest, obj["hash"], progress=progress)

        with ThreadPoolExecutor(max_workers=24) as pool:
            futs = [pool.submit(get_obj, it) for it in objects]
            for f in as_completed(futs):
                f.result()
                progress.inc()
        result["phases"].append(phase(progress, "assets_sample", start, before, len(objects),
                                      progress.snapshot()["bytes_done"]))

    # 4) Fabric loader profile + libraries
    progress = mclaunch.Progress()
    before = mclaunch._DOWNLOAD_SEQ
    start = time.time()
    vid = mclaunch.install_fabric(mc, root, progress)
    result["phases"].append(phase(progress, "fabric_install", start, before,
                                  progress.snapshot()["total"],
                                  progress.snapshot()["bytes_done"]))
    result["fabric_version"] = vid
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mc", action="append", default=[],
                    help="Minecraft version (repeatable); default 1.20.1 and 1.21.1")
    ap.add_argument("--assets", type=int, default=150, help="asset objects sampled per version")
    ap.add_argument("--root", default=str(ROOT / "work" / "perf-root"))
    ap.add_argument("--keep", action="store_true", help="keep the downloaded root (default: delete)")
    args = ap.parse_args()
    versions = args.mc or ["1.20.1", "1.21.1"]
    root = Path(args.root)
    RUNS.mkdir(parents=True, exist_ok=True)
    summary = {"versions": versions, "assets_sample": args.assets, "results": []}
    try:
        for mc in versions:
            if root.exists():
                shutil.rmtree(root)
            root.mkdir(parents=True)
            cold = one_pass(mc, root, "cold", args.assets)
            hot = one_pass(mc, root, "hot", args.assets)
            summary["results"] += [cold, hot]
            for r in (cold, hot):
                print(f"\n{mc} {r['label']}")
                for ph in r["phases"]:
                    print(f"  {ph['phase']:14s} {ph['seconds']:8.2f}s  "
                          f"{ph['bytes']/1048576:8.1f} MB  {ph['mb_per_s']:6.2f} MB/s  "
                          f"files={ph['files']} fail={ph['failures']} retry={ph['retries']}")
            summary["root_bytes"] = dir_size(root) if root.exists() else 0
            print(f"\nroot size: {summary['root_bytes']/1048576:.1f} MB")
    finally:
        cleaned = False
        if root.exists() and not args.keep:
            shutil.rmtree(root)
            cleaned = True
        summary["root_cleaned"] = cleaned
        out = RUNS / "bench.json"
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        (RUNS / "bench.txt").write_text(
            "\n".join(f"{r['mc']} {r['label']} " + " ".join(
                f"{p['phase']}={p['seconds']}s/{p['bytes']}B/{p['mb_per_s']}MBps/fail{p['failures']}"
                for p in r["phases"]) for r in summary["results"]), encoding="utf-8")
        print("result:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
