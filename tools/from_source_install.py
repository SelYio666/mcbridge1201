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



def detect_pcl_root() -> Path | None:
    """Best-effort PCL game directory: env override, PCL Setup.ini, then %APPDATA%/.minecraft."""
    env = os.environ.get("MCBRIDGE_PCL_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    cands = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        cands.append(Path(appdata) / ".minecraft")
        for ini in (Path(appdata) / "PCL" / "Setup.ini",
                    Path(appdata) / "PCL" / "Settings.ini"):
            if ini.is_file():
                try:
                    for line in ini.read_text(encoding="utf-8", errors="replace").splitlines():
                        for key in ("LaunchFolder=", "GameDir=", "GameFolder="):
                            if line.startswith(key):
                                cands.insert(0, Path(line[len(key):].strip()))
                except Exception:  # noqa: BLE001
                    pass
    cands.append(Path.home() / ".minecraft")
    for c in cands:
        if c.is_dir():
            return c
    return None


def write_launcher_profiles(root: Path, version: str) -> Path:
    """Add a custom profile so launchers that read launcher_profiles.json pick the version up."""
    import datetime

    path = root / "launcher_profiles.json"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {}
    profiles = data.setdefault("profiles", {})
    key = f"mcbridge-{version}"
    profiles[key] = {
        "name": f"{version} (mcbridge)",
        "type": "custom",
        "created": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "lastVersionId": version,
        "gameDir": str(root),
    }
    data.setdefault("selectedProfile", key)
    data.setdefault("settings", {"enableSnapshots": False})
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path



def interactive() -> int:
    print("== mcbridge 一键安装到 PCL ==")
    ver = input("要装的版本 [1.21.1]: ").strip() or "1.21.1"
    root = detect_pcl_root()
    if root:
        print("检测到 PCL 游戏目录:", root)
    else:
        raw = input("没有自动找到，请输入 PCL 的游戏目录（包含 versions/ 的 .minecraft）: ").strip()
        if not raw:
            print("已取消")
            return 2
        root = Path(raw)
    print(f"将安装 {ver} 到 {root}")
    if input("继续？[Y/n]: ").strip().lower() in ("n", "no"):
        print("已取消")
        return 2
    rc = install(ver, root, 16)
    if rc == 0:
        path = write_launcher_profiles(root, ver)
        print("已写 launcher_profiles.json:", path)
        try:
            os.startfile(str(root))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
        print("完成：打开 PCL → 刷新版本列表 → 选中", ver, "→ 启动（Java 选 17/21）")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.21.1")
    ap.add_argument("--root", default=".minecraft")
    ap.add_argument("--workers", type=int, default=16)
    if len(sys.argv) == 1:
        return interactive()
    ap.add_argument("--pcl", action="store_true",
                    help="装进 PCL 游戏目录（自动检测），并写 launcher_profiles.json")
    ap.add_argument("--pcl-dir", default=None,
                    help="显式指定 PCL 游戏目录（包含 versions/ 的那个 .minecraft）")
    ap.add_argument("--open", action="store_true", help="装完后打开游戏目录")
    args = ap.parse_args()

    pcl_mode = args.pcl or bool(args.pcl_dir)
    root = Path(args.pcl_dir) if args.pcl_dir else Path(args.root)
    if args.pcl and not args.pcl_dir:
        detected = detect_pcl_root()
        if detected is None:
            print("没有找到 PCL 游戏目录，请用 --pcl-dir 指定（里面有 versions/ 的那个 .minecraft）")
            return 2
        root = detected
        print("PCL 游戏目录:", root)
    rc = install(args.version, root, args.workers)
    if rc == 0 and pcl_mode:
        path = write_launcher_profiles(root, args.version)
        print("已写 launcher_profiles.json:", path)
        print(f"打开 PCL → 版本列表刷新，应能看到 {args.version} → 选中启动（Java 记得选 17/21）")
    if rc == 0 and (args.open or pcl_mode):
        try:
            os.startfile(str(root))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
