#!/usr/bin/env python3
"""Port triage for a folder of mod jars: what blocks a move to another Minecraft/loader line.

Reads only jar structure and metadata (no game launch), then writes a Markdown + JSON report:

    python tools/port_report.py --mods "D:\\path\\to\\mods" --out report.md

Per jar it records loader (Forge mods.toml / Fabric fabric.mod.json), mod id/version, mixin and
access-transformer presence, Kotlin usage, embedded jars, native libraries, loader-API references
and a coarse verdict: EASY / MEDIUM / HARD / BLOCKED. The verdicts are triage, not promises.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

try:
    import tomllib  # py3.11+
except Exception:  # noqa: BLE001
    tomllib = None

BLOCKER_IDS = {"sodium", "embeddium", "iris", "oculus", "distanthorizons", "dh",
               "shaders", "rubidium", "nvidium"}
HARD_LOADER = ("net/minecraftforge/", "net/neoforged/", "cpw/mods/", "org/spongepowered/")


def read_text(z: zipfile.ZipFile, name: str) -> str:
    try:
        return z.read(name).decode("utf-8", "replace")
    except KeyError:
        return ""


def forge_meta(text: str) -> dict:
    if tomllib is None or not text:
        return {}
    try:
        return tomllib.loads(text)
    except Exception:  # noqa: BLE001
        return {}


def analyze(jar: Path) -> dict:
    out = {"jar": jar.name, "size": jar.stat().st_size, "loader": "unknown", "mod_id": "",
           "version": "", "classes": 0, "mixins": 0, "access_transformers": False,
           "kotlin": False, "native_libs": 0, "embedded_jars": 0,
           "forge_refs": 0, "neoforge_refs": 0, "fabric_refs": 0, "blocker": None}
    with zipfile.ZipFile(jar) as z:
        names = z.namelist()
        out["classes"] = sum(1 for n in names if n.endswith(".class"))
        out["mixins"] = sum(1 for n in names if n.endswith(".mixins.json") or ".mixins." in n)
        out["access_transformers"] = any(n.endswith("accesstransformer.cfg") for n in names)
        out["native_libs"] = sum(1 for n in names if n.endswith((".dll", ".so", ".dylib")))
        out["embedded_jars"] = sum(1 for n in names if n.endswith(".jar"))

        fml = read_text(z, "META-INF/mods.toml")
        fabric = read_text(z, "fabric.mod.json")
        if fml:
            out["loader"] = "forge"
            meta = forge_meta(fml)
            mods = meta.get("mods") or []
            if mods:
                out["mod_id"] = str(mods[0].get("modId", ""))
                out["version"] = str(mods[0].get("version", ""))
            deps = meta.get("dependencies") or {}
            out["mandatory_deps"] = [d.get("modId") for ds in deps.values() for d in ds
                                     if str(d.get("mandatory", "")).lower() == "true"]
        elif fabric:
            out["loader"] = "fabric"
            try:
                fj = json.loads(fabric)
                out["mod_id"] = fj.get("id", "")
                out["version"] = fj.get("version", "")
            except Exception:  # noqa: BLE001
                pass
        # constant-pool-ish scan over class bytes
        blob = b"".join(z.read(n) for n in names if n.endswith(".class"))
        out["kotlin"] = b"kotlin/" in blob
        out["forge_refs"] = blob.count(b"net/minecraftforge/")
        out["neoforge_refs"] = blob.count(b"net/neoforged/")
        out["fabric_refs"] = blob.count(b"net/fabricmc/")

    mid = (out["mod_id"] or out["jar"]).lower()
    coremod = any("coremod" in n.lower() for n in names)
    if any(b in mid for b in BLOCKER_IDS):
        out["blocker"] = "render/optimizer core"
    elif out["native_libs"]:
        out["blocker"] = "native libraries"
    elif coremod:
        out["blocker"] = "coremod"
    elif out["loader"] == "unknown" and out["embedded_jars"]:
        out["blocker"] = "loader-level jar (e.g. Connector)"

    if out["blocker"]:
        out["verdict"] = "BLOCKED"
    elif out["access_transformers"] or out["forge_refs"] > 200 or out["mixins"] >= 2:
        out["verdict"] = "HARD"
    elif out["mixins"] >= 1 or out["fabric_refs"] > 50:
        out["verdict"] = "MEDIUM"
    else:
        out["verdict"] = "EASY"
    return out


def render(rows: list[dict]) -> str:
    lines = ["# 移植评估（结构级）", "",
             "只读 jar 结构/元数据，不启动游戏；结论是分诊，不是承诺。", "",
             "| jar | 加载器 | mod id | mixin | AT | Kotlin | 原生库 | 内嵌 jar | 判定 | 阻塞原因 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (x["verdict"], x["jar"])):
        lines.append(f"| {r['jar']} | {r['loader']} | {r['mod_id']} | {r['mixins']} | "
                     f"{'Y' if r['access_transformers'] else ''} | {'Y' if r['kotlin'] else ''} | "
                     f"{r['native_libs']} | {r['embedded_jars']} | **{r['verdict']}** | "
                     f"{r['blocker'] or ''} |")
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    lines += ["", "## 汇总", "", " · ".join(f"{k}={v}" for k, v in sorted(counts.items())), ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mods", required=True)
    ap.add_argument("--out", default="port-report.md")
    ap.add_argument("--json", default="port-report.json")
    args = ap.parse_args()
    mods = Path(args.mods)
    jars = sorted(mods.glob("*.jar"))
    if not jars:
        print("no jars in", mods)
        return 2
    rows = [analyze(j) for j in jars]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render(rows), encoding="utf-8")
    Path(args.json).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(render(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
