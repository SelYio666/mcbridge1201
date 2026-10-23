#!/usr/bin/env python3
"""p178 world: static 80-armor-stand vertex-upload stress scene.

Reuses the p175 world builder, replaces the playerdata with an empty inventory, and adds a data
pack that (on load) fixes time/weather, carves a box in front of spawn and summons 80 static armor
stands (5 x 4 x 4). The scene is intentionally static so the on/off screenshots can be diffed
pixel-for-pixel while the renderer still uploads dynamic vertex buffers every frame.
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
VERTEX_WORLD = INSTANCE / "saves" / "ColdWorldVertex"
TAG_INT = p175.TAG_INT
TAG_BYTE = p175.TAG_BYTE
TAG_FLOAT = p175.TAG_FLOAT
TAG_DOUBLE = p175.TAG_DOUBLE
TAG_STRING = p175.TAG_STRING
TAG_LIST = p175.TAG_LIST
TAG_COMPOUND = p175.TAG_COMPOUND

GRID = [(x, y, z)
        for z in range(75, 79)      # 4 rows in front of the player
        for y in range(67, 71)      # 4 heights (feet at eye level and above)
        for x in range(15, 20)]     # 5 columns
assert len(GRID) == 80


def write_playerdata(path: Path) -> None:
    root = {
        "DataVersion": (TAG_INT, 3955),
        "Dimension": (TAG_STRING, "minecraft:overworld"),
        "Pos": (TAG_LIST, (TAG_DOUBLE, [17.5, 66.0, 70.5])),
        "Motion": (TAG_LIST, (TAG_DOUBLE, [0.0, 0.0, 0.0])),
        "playerGameType": (TAG_INT, 1),
        "SelectedItemSlot": (TAG_INT, 0),
        "Inventory": (TAG_LIST, (TAG_COMPOUND, [])),
        "Health": (TAG_FLOAT, 20.0),
        "foodLevel": (TAG_INT, 20),
        "XpLevel": (TAG_INT, 0),
        "OnGround": (TAG_BYTE, 1),
        "Rotation": (TAG_LIST, (TAG_FLOAT, [0.0, 0.0])),
    }
    p175.write_nbt(path, root)


def write_datapack(world: Path) -> None:
    pack = world / "datapacks" / "p178-vertex"
    (pack / "data" / "minecraft" / "tags" / "function").mkdir(parents=True, exist_ok=True)
    (pack / "data" / "p178" / "function").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"pack_format": 48, "description": "p178 vertex upload stress"}}) + "\n",
        encoding="utf-8")
    (pack / "data" / "minecraft" / "tags" / "function" / "load.json").write_text(
        json.dumps({"values": ["p178:load"]}) + "\n", encoding="utf-8")
    (pack / "data" / "minecraft" / "tags" / "function" / "tick.json").write_text(
        json.dumps({"values": ["p178:tick"]}) + "\n", encoding="utf-8")
    # Lock the camera every tick: mouse focus/position can otherwise rotate the player between
    # the A/B runs and make a pixel diff meaningless.
    (pack / "data" / "p178" / "function" / "tick.mcfunction").write_text(
        "tp @a 17.5 66.0 70.5 0.0 0.0\n", encoding="utf-8")
    lines = [
        "gamerule sendCommandFeedback false",
        "gamerule doDaylightCycle false",
        "gamerule doWeatherCycle false",
        "gamerule randomTickSpeed 0",
        "time set 6000",
        "weather clear",
        # Carve a box in front of the player so the armor stands float in clear view.
        "fill 14 66 74 20 71 79 minecraft:air",
    ]
    for x, y, z in GRID:
        # 0.5-centered on x/z; feet at the given y. NoAI/NoGravity keeps the scene static.
        lines.append(
            f"summon minecraft:armor_stand {x + 0.5:.1f} {y}.0 {z + 0.5:.1f} "
            "{NoAI:1b,NoGravity:1b,Invulnerable:1b,Silent:1b}")
    (pack / "data" / "p178" / "function" / "load.mcfunction").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


def tune_options() -> None:
    options = INSTANCE / "options.txt"
    values: dict[str, str] = {}
    if options.exists():
        for line in options.read_text(encoding="utf-8", errors="replace").splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                values[key] = value
    values.update({
        "renderClouds": "false",
        "particles": "minimal",
        "maxFps": "260",
        "enableVsync": "false",
        "renderDistance": "8",
        "simulationDistance": "8",
        "pauseOnLostFocus": "false",
        "guiScale": "2",
        "fov": "70",
    })
    options.write_text("".join(f"{k}:{v}\n" for k, v in values.items()), encoding="utf-8")


def prepare() -> dict:
    info = p175.prepare(out_world=VERTEX_WORLD, instance=INSTANCE)
    uid = info["uuid"]
    write_playerdata(VERTEX_WORLD / "playerdata" / f"{uid}.dat")
    write_datapack(VERTEX_WORLD)
    tune_options()
    return {
        **info,
        "world": str(VERTEX_WORLD),
        "armor_stands": len(GRID),
        "grid": {"x": [15, 19], "y": [67, 70], "z": [75, 78]},
        "scene": "static (time 6000, no weather/clouds, empty hand, NoAI armor stands)",
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
