#!/usr/bin/env python3
"""Fetch and pin the exact Fabric 1.21.4 target environment.

B01 needs one frozen target, not a range: the client jar, the official mappings, the intermediary
mappings, the Fabric API build and the loader build are all pinned by URL and SHA-256 in
`manifests/target-fabric-1.21.4.lock.json`, so "what is 1.21.4 for this project" has one answer.

    python tools/fetch_target_1214.py
    python tools/fetch_target_1214.py --force        # re-download even if cached

Nothing is downloaded that is already present and hash-correct. Game jars stay under `work/`
(gitignored); only the lock file is committed. Mojang's EULA applies to the client jar.
Exit codes: 0 pinned, 1 download/hash mismatch, 2 usage problem.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "target"
LOCK = ROOT / "manifests" / "target-fabric-1.21.4.lock.json"
VERSION = "1.21.4"
SCHEMA = "target-env-lock-1"

FABRIC = {
    "intermediary": (
        "intermediary-1.21.4-v2.jar",
        "https://maven.fabricmc.net/net/fabricmc/intermediary/1.21.4/intermediary-1.21.4-v2.jar",
        "1.21.4",
    ),
    "loader": (
        "fabric-loader-0.16.14.jar",
        "https://maven.fabricmc.net/net/fabricmc/fabric-loader/0.16.14/fabric-loader-0.16.14.jar",
        "0.16.14",
    ),
    "api": (
        "fabric-api-0.119.4+1.21.4.jar",
        "https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/0.119.4+1.21.4/"
        "fabric-api-0.119.4+1.21.4.jar",
        "0.119.4+1.21.4",
    ),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, dst: Path, attempts: int = 4) -> None:
    """Download with retries: this network drops connections mid-transfer."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, tmp.open("wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            tmp.replace(dst)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:  # noqa: PERF203
            last = exc
            print(f"  attempt {attempt}/{attempts} failed: {exc}", file=sys.stderr)
            time.sleep(2 * attempt)
    raise SystemExit(f"download failed after {attempts} attempts: {url} ({last})")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)

    with urllib.request.urlopen(
            "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json", timeout=90) as r:
        manifest = json.load(r)
    entries = [v for v in manifest["versions"] if v["id"] == VERSION]
    if not entries:
        raise SystemExit(f"{VERSION} is not in the Mojang version manifest")
    entry = entries[0]
    with urllib.request.urlopen(entry["url"], timeout=90) as r:
        meta = json.load(r)

    java = meta["javaVersion"]
    records = {}

    def record(key, role, path: Path, url: str, expected_sha1: str | None, version: str | None):
        actual_sha1 = sha1_file(path) if expected_sha1 else None
        if expected_sha1 and actual_sha1 != expected_sha1:
            raise SystemExit(f"{path.name}: sha1 {actual_sha1} != expected {expected_sha1}")
        records[key] = {
            "role": role,
            "version": version,
            "url": url,
            "path": path.relative_to(ROOT).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
            "sha1": actual_sha1,
            "sha1Ok": (actual_sha1 == expected_sha1) if expected_sha1 else None,
        }
        print(f"  {key:14} {records[key]['sha256'][:16]}  {path.name}")

    downloads = [
        ("clientJar", "target client jar", f"client-{VERSION}.jar",
         meta["downloads"]["client"], meta["downloads"]["client"].get("sha1")),
        ("clientMappings", "official (Mojang) client mappings", f"client-{VERSION}-mappings.txt",
         meta["downloads"]["client_mappings"], meta["downloads"]["client_mappings"].get("sha1")),
    ]
    print(f"target {VERSION}: java {java['majorVersion']} ({java['component']})")
    for key, role, name, d, expected in downloads:
        dst = WORK / name
        if args.force or not dst.is_file():
            print(f"downloading {name} ...")
            fetch(d["url"], dst)
        record(key, role, dst, d["url"], expected, None)

    for key, (name, url, ver) in FABRIC.items():
        dst = WORK / name
        if args.force or not dst.is_file():
            print(f"downloading {name} ...")
            fetch(url, dst)
        record(key, "fabric " + key, dst, url, None, ver)

    lock = {
        "schemaVersion": SCHEMA,
        "minecraft": VERSION,
        "type": entry["type"],
        "releaseTime": entry.get("releaseTime"),
        "javaVersion": {"component": java["component"], "majorVersion": java["majorVersion"]},
        "classMajorMax": java["majorVersion"] + 44,
        "namespace": "intermediary",
        "artifacts": records,
        "notIncluded": [
            "The bridge compile stub: it is derived locally from clientJar + intermediary by"
            " `mcbridge1201 remap-jar` and recorded by hash in targets/fabric-1.21.4.json.",
            "Server jar, assets and libraries: not needed for the static delta stage.",
        ],
        "note": "Pinned by URL and hash. Game jars live under work/ (gitignored); the client jar is"
                " Mojang's and the EULA applies.",
    }
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"wrote {LOCK.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
