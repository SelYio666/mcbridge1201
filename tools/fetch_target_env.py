"""Fetch the exact target environment for static analysis (Minecraft 1.21.1 + Fabric).

Downloads (local only, never committed):
  - official 1.21.1 client jar (for the class/member index; Mojang EULA applies)
  - official 1.21.1 client mappings (Mojang names; used by the Forge/NeoForge route)
  - Fabric intermediary 1.21.1 / 1.20.1
  - Fabric API 1.21.1 (bundle jar, nested modules indexed recursively)
  - Fabric Loader compatible with 1.21.1

Writes manifests/environment.lock.json with URLs, sizes and SHA-256.
"""
from __future__ import annotations

import hashlib
import json
import os

from fetchlib import download, http_json, now_iso, write_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "work", "target")
MANIFESTS = os.path.join(ROOT, "manifests")


def sha1_of(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    os.makedirs(WORK, exist_ok=True)
    vm = http_json("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
    wanted = {"1.21.1", "1.20.1"}
    entries = []
    for v in vm["versions"]:
        if v["id"] not in wanted:
            continue
        meta = http_json(v["url"])
        client = meta["downloads"]["client"]
        jar = os.path.join(WORK, f"client-{v['id']}.jar")
        rec = download(client["url"], jar)
        ok_sha1 = sha1_of(jar) == client["sha1"]
        cm = meta["downloads"].get("client_mappings")
        cmrec = None
        if cm:
            cmpath = os.path.join(WORK, f"client-{v['id']}-mappings.txt")
            cmrec = download(cm["url"], cmpath)
            cmrec["sha1Ok"] = sha1_of(cmpath) == cm["sha1"]
        entries.append({
            "minecraft": v["id"],
            "type": v["type"],
            "releaseTime": v["releaseTime"],
            "javaVersion": meta.get("javaVersion"),
            "clientJar": {**rec, "sha1": client["sha1"], "sha1Ok": ok_sha1},
            "clientMappings": cmrec,
        })
        print(f"[target] {v['id']} client jar {rec['size']} bytes sha1ok={ok_sha1}")

    locked = {"generatedAt": now_iso(), "minecraft": entries, "fabric": {}}

    # Fabric intermediary + loader + API for 1.21.1
    for ver in ("1.20.1", "1.21.1"):
        url = f"https://maven.fabricmc.net/net/fabricmc/intermediary/{ver}/intermediary-{ver}-v2.jar"
        rec = download(url, os.path.join(WORK, f"intermediary-{ver}-v2.jar"))
        locked["fabric"][f"intermediary-{ver}"] = rec

    loaders = http_json("https://meta.fabricmc.net/v2/versions/loader/1.21.1")
    stable = next((l for l in loaders if l["loader"]["stable"]), loaders[0])
    lv = stable["loader"]["version"]
    lurl = f"https://maven.fabricmc.net/net/fabricmc/fabric-loader/{lv}/fabric-loader-{lv}.jar"
    locked["fabric"]["loader"] = {**download(lurl, os.path.join(WORK, f"fabric-loader-{lv}.jar")), "version": lv}

    fapi_ver = "0.102.0+1.21.1"
    fapi_url = f"https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/{fapi_ver}/fabric-api-{fapi_ver}.jar"
    locked["fabric"]["api"] = {**download(fapi_url, os.path.join(WORK, f"fabric-api-{fapi_ver}.jar")), "version": fapi_ver}

    srcapi_ver = "0.92.12+1.20.1"
    srcapi_url = f"https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/{srcapi_ver}/fabric-api-{srcapi_ver}.jar"
    locked["fabric"]["api-1.20.1"] = {**download(srcapi_url, os.path.join(WORK, f"fabric-api-{srcapi_ver}.jar")), "version": srcapi_ver}

    write_json(os.path.join(MANIFESTS, "environment.lock.json"), locked)
    print("wrote manifests/environment.lock.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
