#!/usr/bin/env python3
"""p181 world: unlocked held map that updates while the player moves, then a normal /stop exit.

- map_1.dat is written with locked=0 so the server sends map color updates as the player moves;
- a data pack teleports the player 8 blocks south and back every second, forcing at least one
  second atlas upload (`map-atlas update`);
- after 400 ticks the data pack runs `stop`, so the integrated server disconnects normally and
  the map renderer's clear/close path runs (`map-atlas clear`, `map-atlas close`, keep-dummy).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P175_PATH = ROOT / "runs" / "p175-map-atlas" / "make_world.py"
_spec = importlib.util.spec_from_file_location("p175_make_world", P175_PATH)
p175 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(p175)

INSTANCE = p175.INSTANCE
UPDATE_WORLD = INSTANCE / "saves" / "ColdWorldMapUpdate"
TAG_INT = p175.TAG_INT
TAG_BYTE = p175.TAG_BYTE
TAG_STRING = p175.TAG_STRING
TAG_BYTE_ARRAY = p175.TAG_BYTE_ARRAY
TAG_LIST = p175.TAG_LIST
TAG_COMPOUND = p175.TAG_COMPOUND


def write_unlocked_map(path: Path) -> None:
    state = {
        "dimension": (TAG_STRING, "minecraft:overworld"),
        "xCenter": (TAG_INT, 0),
        "zCenter": (TAG_INT, 0),
        "scale": (TAG_BYTE, 0),
        "colors": (TAG_BYTE_ARRAY, p175.map_colors()),
        "trackingPosition": (TAG_BYTE, 1),
        "unlimitedTracking": (TAG_BYTE, 0),
        "locked": (TAG_BYTE, 0),
        "banners": (TAG_LIST, (TAG_COMPOUND, [])),
        "frames": (TAG_LIST, (TAG_COMPOUND, [])),
    }
    p175.write_nbt(path, {"DataVersion": (TAG_INT, 3955), "data": (TAG_COMPOUND, state)})


def write_datapack(world: Path) -> None:
    pack = world / "datapacks" / "p181-map-update"
    for part in (("data", "minecraft", "tags", "function"), ("data", "p181", "function")):
        (pack.joinpath(*part)).mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"pack_format": 48, "description": "p181 map update + exit"}}) + "\n",
        encoding="utf-8")
    (pack / "data" / "minecraft" / "tags" / "function" / "load.json").write_text(
        json.dumps({"values": ["p181:load"]}) + "\n", encoding="utf-8")
    (pack / "data" / "minecraft" / "tags" / "function" / "tick.json").write_text(
        json.dumps({"values": ["p181:tick"]}) + "\n", encoding="utf-8")
    (pack / "data" / "p181" / "function" / "load.mcfunction").write_text(
        "gamerule sendCommandFeedback false\n"
        "scoreboard objectives add p181 dummy\n"
        "fill 14 66 74 20 71 79 minecraft:air\n",
        encoding="utf-8")
    # The normal exit is triggered by a tiny client probe (p181probe), because /stop is not part
    # of the integrated-server command tree and datapack functions run at permission level 2.
    (pack / "data" / "p181" / "function" / "tick.mcfunction").write_text(
        "scoreboard players add @a p181 1\n"
        "execute as @a if score @s p181 matches 20 run tp @s 17.5 66.0 78.5 0.0 0.0\n"
        "execute as @a if score @s p181 matches 40 run tp @s 17.5 66.0 70.5 0.0 0.0\n"
        "execute as @a if score @s p181 matches 40 run scoreboard players set @s p181 0\n",
        encoding="utf-8")


def prepare() -> dict:
    info = p175.prepare(out_world=UPDATE_WORLD, instance=INSTANCE)
    write_unlocked_map(UPDATE_WORLD / "data" / "map_1.dat")
    write_datapack(UPDATE_WORLD)
    probe = ROOT / "work" / "tmp" / "p181-probe.jar"
    if probe.exists():
        import shutil
        shutil.copy2(probe, INSTANCE / "mods" / "p181-probe.jar")
    return {
        **info,
        "world": str(UPDATE_WORLD),
        "mapId": 1,
        "locked": False,
        "teleport": [[17.5, 66.0, 70.5], [17.5, 66.0, 78.5]],
        "probe": str(probe) if probe.exists() else "missing (run build_probe.py first)",
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
