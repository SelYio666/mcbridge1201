#!/usr/bin/env python3
"""p200 world: three 4096x4096 atlases, per-tile verification and a visible three-map layout.

Reuses the p175/p181 world builder (map_1.dat unlocked + Fabric API + the ported ImmediatelyFast
jar in the instance mods dir), adds a p200 data pack and installs the p200 probe jar.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P181_PATH = ROOT / "runs" / "p181-map-atlas-lifecycle" / "make_world.py"
_spec = importlib.util.spec_from_file_location("p181_make_world", P181_PATH)
p181 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(p181)

INSTANCE = p181.INSTANCE
WORLD = INSTANCE / "saves" / "ColdWorldAtlasLayout"
PROBE = ROOT / "work" / "tmp" / "p200-probe.jar"


def write_datapack(world: Path) -> None:
    pack = world / "datapacks" / "p200-atlas-layout"
    for part in (("data", "minecraft", "tags", "function"), ("data", "p200", "function")):
        (pack.joinpath(*part)).mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"pack_format": 48, "description": "p200 atlas layout"}}) + "\n",
        encoding="utf-8")
    (pack / "data" / "minecraft" / "tags" / "function" / "load.json").write_text(
        json.dumps({"values": ["p200:load"]}) + "\n", encoding="utf-8")
    (pack / "data" / "minecraft" / "tags" / "function" / "tick.json").write_text(
        json.dumps({"values": ["p200:tick"]}) + "\n", encoding="utf-8")
    (pack / "data" / "p200" / "function" / "load.mcfunction").write_text(
        "gamerule sendCommandFeedback false\n"
        "scoreboard objectives add p200 dummy\n"
        "fill 14 66 74 20 71 79 minecraft:air\n",
        encoding="utf-8")
    (pack / "data" / "p200" / "function" / "tick.mcfunction").write_text(
        "scoreboard players add @a p200 1\n", encoding="utf-8")


def prepare() -> dict:
    info = p181.prepare()
    # Refresh in place instead of deleting the tree: a re-run must not depend on being allowed to
    # bulk-delete the previous copy.
    shutil.copytree(INSTANCE / "saves" / "ColdWorldMapUpdate", WORLD, dirs_exist_ok=True)
    write_datapack(WORLD)
    if PROBE.exists():
        shutil.copy2(PROBE, INSTANCE / "mods" / "p200-probe.jar")
    else:
        print(f"warning: probe jar missing ({PROBE}); run build_probe.py first", file=sys.stderr)
    return {
        **info,
        "world": str(WORLD),
        "probe": str(PROBE) if PROBE.exists() else "missing (run build_probe.py first)",
    }


def main() -> int:
    try:
        info = prepare()
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for key, value in info.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
