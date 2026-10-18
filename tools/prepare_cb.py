"""Prepare the CenturyBridge working set (P0 real conversion attempt).

Creates work/cb/data/{jars,mappings,segments} and extracts the intermediary .tiny
files the engine expects (it reads plain `.tiny`, not the Maven jars). Game jars are
local only and never committed.
"""
from __future__ import annotations

import json
import os
import shutil
import zipfile

from fetchlib import download, now_iso, write_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CB = os.path.join(ROOT, "work", "cb")
DATA = os.path.join(CB, "data")
VERSIONS = ["1.20.1", "1.20.2", "1.20.3", "1.20.4", "1.20.5", "1.20.6", "1.21", "1.21.1"]


def main() -> int:
    for d in ("jars", "mappings", "segments"):
        os.makedirs(os.path.join(DATA, d), exist_ok=True)
    os.makedirs(os.path.join(CB, "out"), exist_ok=True)

    # game jars copied from the locked target set
    for ver in ("1.20.1", "1.21.1"):
        src = os.path.join(ROOT, "work", "target", f"client-{ver}.jar")
        dst = os.path.join(DATA, "jars", f"client-{ver}-obf.jar")
        if not os.path.exists(dst):
            shutil.copy(src, dst)
        print(f"[cb] obf jar {ver}: {os.path.getsize(dst)} bytes")

    # intermediary mappings -> plain .tiny
    for ver in VERSIONS:
        jar = os.path.join(ROOT, "work", "target", f"intermediary-{ver}-v2.jar")
        if not os.path.exists(jar):
            rec = download(f"https://maven.fabricmc.net/net/fabricmc/intermediary/{ver}/intermediary-{ver}-v2.jar", jar)
            print(f"[cb] downloaded intermediary {ver} sha256={rec['sha256'][:12]}")
        tiny = os.path.join(DATA, "mappings", f"intermediary-{ver}.tiny")
        with zipfile.ZipFile(jar) as zf, zf.open("mappings/mappings.tiny") as src, open(tiny, "wb") as out:
            out.write(src.read())
        print(f"[cb] tiny {ver}: {os.path.getsize(tiny)} bytes")

    write_json(os.path.join(CB, "prepare.json"), {
        "generatedAt": now_iso(),
        "chain": VERSIONS,
        "note": "game jars are local-only; intermediary mappings are Fabric MIT-licensed data",
    })
    print("cb working set:", CB)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
