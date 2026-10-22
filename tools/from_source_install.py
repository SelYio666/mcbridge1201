#!/usr/bin/env python3
"""Install Minecraft (vanilla) from the public download sources, in one command.

    python tools/from_source_install.py --version 1.21.1 --root D:\\MC

What it does: version manifest -> version json -> client jar -> libraries (+ Windows
natives) -> asset index -> asset objects, verifying sha1, falling back to the BMCLAPI
mirror on failure. Result is a normal .minecraft that PCL/HMCL/our launcher can use.

Only stdlib is required. Downloads are resumable per file via Range when a .part file
is left behind, and every asset is skipped when already present with the right size.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

UA = {"User-Agent": "mcbridge-from-source/1.0"}
MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
ASSET_OFFICIAL = "https://resources.download.minecraft.net"
ASSET_MIRROR = "https://bmclapi2.bangbang93.com/assets"
MAVEN_MIRROR = "https://bmclapi2.bangbang93.com/maven"


def mirror_of(url: str) -> str | None:
    if url.startswith(ASSET_OFFICIAL + "/"):
        return ASSET_MIRROR + url[len(ASSET_OFFICIAL):]
    if url.startswith("https://libraries.minecraft.net/"):
        return MAVEN_MIRROR + url[len("https://libraries.minecraft.net"):]
    return None


def http_get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_json(url: str):
    return json.loads(http_get(url))


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, sha1: str | None = None, retries: int = 3) -> bool:
    """Download url to dest with mirror fallback and sha1 check. Returns True if final file is valid."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and (sha1 is None or sha1_file(dest) == sha1):
        return True
    candidates = [url]
    m = mirror_of(url)
    if m:
        candidates.append(m)
    part = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(retries):
        for cand in candidates:
            try:
                req = urllib.request.Request(cand, headers=UA)
                with urllib.request.urlopen(req, timeout=60) as r, open(part, "wb") as f:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                if sha1 and sha1_file(part) != sha1:
                    part.unlink(missing_ok=True)
                    continue
                part.replace(dest)
                return True
            except Exception:  # noqa: BLE001 - try the next candidate
                part.unlink(missing_ok=True)
        time.sleep(1.5 * (attempt + 1))
    return False


def allowed(lib: dict) -> bool:
    rules = lib.get("rules")
    if not rules:
        return True
    ok = False
    for rule in rules:
        action = rule.get("action")
        os_name = (rule.get("os") or {}).get("name")
        if os_name in (None, "windows"):
            ok = action == "allow"
    return ok


def install(version: str, root: Path, workers: int = 16) -> int:
    root.mkdir(parents=True, exist_ok=True)
    print(f"[1/5] manifest ...")
    manifest = get_json(MANIFEST)
    entry = next((v for v in manifest["versions"] if v["id"] == version), None)
    if not entry:
        print("version not found:", version)
        return 2
    data = get_json(entry["url"])
    vid = data["id"]
    vdir = root / "versions" / vid
    (vdir).mkdir(parents=True, exist_ok=True)
    (vdir / f"{vid}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"[2/5] client jar ({version}) ...")
    client = data["downloads"]["client"]
    if not download(client["url"], vdir / f"{vid}.jar", client.get("sha1")):
        print("client jar failed")
        return 3

    print("[3/5] libraries (+ natives) ...")
    natives_dir = vdir / "natives"
    natives_dir.mkdir(parents=True, exist_ok=True)
    libs = [l for l in data.get("libraries", []) if allowed(l)]
    jobs = []
    for lib in libs:
        art = lib.get("downloads", {}).get("artifact")
        win = (lib.get("natives") or {}).get("windows")
        is_native = bool(win) or "natives-windows" in lib.get("name", "")
        if art:
            jobs.append((art["url"], root / "libraries" / art["path"], art.get("sha1"), is_native))
        if win:
            cl = lib.get("downloads", {}).get("classifiers", {}).get(win)
            if cl:
                jobs.append((cl["url"], root / "libraries" / cl["path"], cl.get("sha1"), True))
    failed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futs = {}
        for job in jobs:
            url, path, sha1, is_native = job
            futs[pool.submit(download, url, path, sha1)] = (path, is_native)
        for i, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            path, is_native = futs[fut]
            if not fut.result():
                failed += 1
                print("  lib failed:", path.name)
            elif is_native and path.suffix == ".jar":
                try:
                    with zipfile.ZipFile(path) as z:
                        for name in z.namelist():
                            if name.endswith((".dll", ".so", ".dylib")):
                                with z.open(name) as src, open(natives_dir / Path(name).name, "wb") as dst:
                                    dst.write(src.read())
                except Exception as exc:  # noqa: BLE001
                    print("  native extract failed:", path.name, exc)
            if i % 20 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} libraries")
    if failed:
        print(f"libraries failed: {failed}")

    print("[4/5] asset index ...")
    idx_meta = data["assetIndex"]
    idx_path = root / "assets" / "indexes" / f"{idx_meta['id']}.json"
    if not download(idx_meta["url"], idx_path, idx_meta.get("sha1")):
        print("asset index failed")
        return 4
    index = json.loads(idx_path.read_text(encoding="utf-8"))
    objs = {o["hash"]: o for o in index["objects"].values()}

    print(f"[5/5] assets ({len(objs)} objects) ...")
    def one(h: str) -> bool:
        dst = root / "assets" / "objects" / h[:2] / h
        if dst.exists() and dst.stat().st_size > 0:
            return True
        return download(f"{ASSET_OFFICIAL}/{h[:2]}/{h}", dst, h)

    ok = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(one, h) for h in objs]
        for i, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            if fut.result():
                ok += 1
            if i % 500 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} assets ok={ok}")
    print(f"done: {vdir}")
    print(f"assets ok {ok}/{len(objs)}; launch/verify with:")
    print(f'  python launcher/mclaunch.py verify {vid} "{root}"')
    print(f'  python launcher/mclaunch.py launch {vid} "{root}" 你的名字')
    return 0 if ok == len(objs) and not failed else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.21.1")
    ap.add_argument("--root", default=".minecraft")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    return install(args.version, Path(args.root), args.workers)


if __name__ == "__main__":
    sys.exit(main())
