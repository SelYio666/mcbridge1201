#!/usr/bin/env python3
"""Fetch the 1.21.4 library closure (classpath jars, no natives) and pin it by hash.

Why this is B03 infrastructure and not busywork: every remaining 1.21.4 rule that needs a bridge
(descriptor changes such as GuiGraphics.method_25290 gaining a RenderType resolver) compiles
against this closure. Without it `build_bridges.py --profile targets/fabric-1.21.4.json` has an
empty `indices.libs` and nothing can be compiled for the target.

    python tools/fetch_target_libs.py
    python tools/fetch_target_libs.py --force

Downloads into work/target/libs-1214/<maven path> (gitignored), verifies piston's sha1, and writes
manifests/target-fabric-1.21.4-libs.lock.json with the sha256 of every jar plus the exact
classpath order.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "target" / "libs-1214"
LOCK = ROOT / "manifests" / "target-fabric-1.21.4-libs.lock.json"
VERSION = "1.21.4"
SCHEMA = "target-libs-lock-1"


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, dst: Path, attempts: int = 4) -> None:
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
            print(f"  attempt {attempt}/{attempts} failed for {dst.name}: {exc}", file=sys.stderr)
            time.sleep(2 * attempt)
    raise SystemExit(f"download failed: {url} ({last})")


def windows_allowed(lib: dict) -> bool:
    rules = lib.get("rules")
    if not rules:
        return True
    for rule in rules:
        os_name = (rule.get("os") or {}).get("name")
        if rule.get("action") == "allow" and os_name in (None, "windows"):
            return True
    return False


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
    entry = next(v for v in manifest["versions"] if v["id"] == VERSION)
    with urllib.request.urlopen(entry["url"], timeout=90) as r:
        meta = json.load(r)

    records = []
    skipped = []
    for lib in meta["libraries"]:
        downloads = lib.get("downloads") or {}
        art = downloads.get("artifact")
        name = lib.get("name", "")
        if not art:
            skipped.append({"name": name, "why": "no artifact download"})
            continue
        if "natives" in name:
            skipped.append({"name": name, "why": "native jar, not a classpath entry"})
            continue
        if not windows_allowed(lib):
            skipped.append({"name": name, "why": "rules exclude windows"})
            continue
        dst = WORK / art["path"]
        if args.force or not dst.is_file():
            fetch(art["url"], dst)
        actual = sha1_file(dst)
        if actual != art["sha1"]:
            raise SystemExit(f"{dst}: sha1 {actual} != {art['sha1']}")
        records.append({
            "name": name,
            "path": dst.relative_to(ROOT).as_posix(),
            "size": dst.stat().st_size,
            "sha256": sha256_file(dst),
            "sha1Ok": True,
        })

    total = sum(r["size"] for r in records)
    lock = {
        "schemaVersion": SCHEMA,
        "minecraft": VERSION,
        "source": "piston-meta version json 'libraries' (windows, classpath jars only)",
        "count": len(records),
        "totalBytes": total,
        "classpath": [r["path"] for r in records],
        "libraries": records,
        "skipped": skipped,
        "note": "Compile/runtime classpath for the target. Natives are excluded: they are for"
                " launching the game, not for javac. Every entry carries sha256; piston's sha1 was"
                " verified at download time.",
    }
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"pinned {len(records)} library jar(s), {total / 1048576:.1f} MB")
    print(f"skipped {len(skipped)} entrie(s) (natives / non-windows)")
    print(f"wrote {LOCK.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
