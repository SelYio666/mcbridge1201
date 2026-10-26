#!/usr/bin/env python3
"""p194 world: third-atlas + cross-atlas same-frame scene.

Reuses the p175/p181 world builder (map_1.dat unlocked + Fabric API + the ported ImmediatelyFast
jar in the instance mods dir), adds a p194 data pack and installs the p194 probe jar. The probe
assigns 2050 map ids, draws map 1/1025/2049 in one HUD frame, then requests a normal client stop.
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
THIRD_WORLD = INSTANCE / "saves" / "ColdWorldAtlasThird"
PROBE = ROOT / "work" / "tmp" / "p194-probe.jar"


def write_datapack(world: Path) -> None:
    pack = world / "datapacks" / "p194-atlas-third"
    for part in (("data", "minecraft", "tags", "function"), ("data", "p194", "function")):
        (pack.joinpath(*part)).mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"pack_format": 48, "description": "p194 atlas third"}}) + "\n",
        encoding="utf-8")
    (pack / "data" / "minecraft" / "tags" / "function" / "load.json").write_text(
        json.dumps({"values": ["p194:load"]}) + "\n", encoding="utf-8")
    (pack / "data" / "minecraft" / "tags" / "function" / "tick.json").write_text(
        json.dumps({"values": ["p194:tick"]}) + "\n", encoding="utf-8")
    (pack / "data" / "p194" / "function" / "load.mcfunction").write_text(
        "gamerule sendCommandFeedback false\n"
        "scoreboard objectives add p194 dummy\n"
        "fill 14 66 74 20 71 79 minecraft:air\n",
        encoding="utf-8")
    (pack / "data" / "p194" / "function" / "tick.mcfunction").write_text(
        "scoreboard players add @a p194 1\n", encoding="utf-8")


def prepare() -> dict:
    info = p181.prepare()
    if THIRD_WORLD.exists():
        shutil.rmtree(THIRD_WORLD)
    shutil.copytree(INSTANCE / "saves" / "ColdWorldMapUpdate", THIRD_WORLD)
    write_datapack(THIRD_WORLD)
    if PROBE.exists():
        shutil.copy2(PROBE, INSTANCE / "mods" / "p194-probe.jar")
    else:
        print(f"warning: probe jar missing ({PROBE}); run build_probe.py first", file=sys.stderr)
    return {
        **info,
        "world": str(THIRD_WORLD),
        "third_atlas_map_id": 2049,
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
