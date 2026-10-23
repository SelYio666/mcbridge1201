#!/usr/bin/env python3
"""p177 world: two atlas maps + an item frame holding map 2.

Reuses the p175 world builder (map 1 + playerdata + mods/options), then:
  * writes ``data/map_2.dat`` with a different pattern;
  * puts map 2 in hotbar slot 1 (so the server sends its state) and keeps map 1 in slot 0;
  * adds a tiny data pack whose ``load`` function places an item frame with map 2 two blocks in
    front of the spawn point (player yaw 0 = south, frame Facing 2 = north).

The result is a singleplayer scene where the held map (id 1) and the framed map (id 2) are both
visible in the screenshot and the log must show both atlas bindings.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
P175_PATH = ROOT / "runs" / "p175-map-atlas" / "make_world.py"

_spec = importlib.util.spec_from_file_location("p175_make_world", P175_PATH)
p175 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(p175)

INSTANCE = p175.INSTANCE
EDGE_WORLD = INSTANCE / "saves" / "ColdWorldMapEdge"
USERNAME = p175.USERNAME
TAG_INT = p175.TAG_INT
TAG_BYTE = p175.TAG_BYTE
TAG_FLOAT = p175.TAG_FLOAT
TAG_DOUBLE = p175.TAG_DOUBLE
TAG_STRING = p175.TAG_STRING
TAG_BYTE_ARRAY = p175.TAG_BYTE_ARRAY
TAG_LIST = p175.TAG_LIST
TAG_COMPOUND = p175.TAG_COMPOUND

# Distinct from map 1 (red/white/green/blue checkerboard + yellow diagonal):
# cyan/purple vertical stripes, a white cross and a magenta centre.
CYAN = (23 << 2)
PURPLE = (24 << 2)
MAGENTA = (16 << 2)
WHITE = (8 << 2)
BLACK = (29 << 2)


def map2_colors() -> bytes:
    data = bytearray(128 * 128)
    for z in range(128):
        for x in range(128):
            if x < 8 or x >= 120 or z < 8 or z >= 120:
                color = BLACK
            elif 58 <= x < 70 or 58 <= z < 70:
                color = WHITE
            elif 56 <= x < 72 and 56 <= z < 72:
                color = MAGENTA
            else:
                color = CYAN if (x // 8) % 2 == 0 else PURPLE
            data[x + z * 128] = color
    return bytes(data)


def write_map2(path: Path) -> None:
    state = {
        "dimension": (TAG_STRING, "minecraft:overworld"),
        "xCenter": (TAG_INT, 0),
        "zCenter": (TAG_INT, 0),
        "scale": (TAG_BYTE, 0),
        "colors": (TAG_BYTE_ARRAY, map2_colors()),
        "trackingPosition": (TAG_BYTE, 1),
        "unlimitedTracking": (TAG_BYTE, 0),
        "locked": (TAG_BYTE, 1),
        "banners": (TAG_LIST, (TAG_COMPOUND, [])),
        "frames": (TAG_LIST, (TAG_COMPOUND, [])),
    }
    p175.write_nbt(path, {"DataVersion": (TAG_INT, 3955), "data": (TAG_COMPOUND, state)})


def write_playerdata(path: Path) -> None:
    def map_item(slot: int, map_id: int) -> dict:
        return {
            "Slot": (TAG_BYTE, slot),
            "id": (TAG_STRING, "minecraft:filled_map"),
            "count": (TAG_INT, 1),
            "components": (TAG_COMPOUND, {"minecraft:map_id": (TAG_INT, map_id)}),
        }

    root = {
        "DataVersion": (TAG_INT, 3955),
        "Dimension": (TAG_STRING, "minecraft:overworld"),
        "Pos": (TAG_LIST, (TAG_DOUBLE, [17.5, 66.0, 70.5])),
        "Motion": (TAG_LIST, (TAG_DOUBLE, [0.0, 0.0, 0.0])),
        "playerGameType": (TAG_INT, 1),
        "SelectedItemSlot": (TAG_INT, 0),
        # The server's inventory tick sends map updates for both stacks; this is what makes the
        # framed map's state available on the client before the frame is rendered.
        "Inventory": (TAG_LIST, (TAG_COMPOUND, [map_item(0, 1), map_item(1, 2)])),
        "Health": (TAG_FLOAT, 20.0),
        "foodLevel": (TAG_INT, 20),
        "XpLevel": (TAG_INT, 0),
        "OnGround": (TAG_BYTE, 1),
        "Rotation": (TAG_LIST, (TAG_FLOAT, [0.0, 0.0])),
    }
    p175.write_nbt(path, root)


def write_datapack(world: Path) -> None:
    pack = world / "datapacks" / "p177-mapframe"
    (pack / "data" / "minecraft" / "tags" / "function").mkdir(parents=True, exist_ok=True)
    (pack / "data" / "p177" / "function").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"pack_format": 48, "description": "p177 map frame"}}) + "\n",
        encoding="utf-8")
    (pack / "data" / "minecraft" / "tags" / "function" / "load.json").write_text(
        json.dumps({"values": ["p177:load"]}) + "\n", encoding="utf-8")
    # The player spawns at (17.5,66,70.5) facing +Z (yaw 0 = south). Put the frame two blocks in
    # front, one block above the ground, with its front facing north (Facing 2) toward the player.
    # The stone at z=74 is the supporting block behind the frame.
    function = """setblock 17 66 73 minecraft:air
setblock 17 67 73 minecraft:air
setblock 17 68 73 minecraft:air
setblock 17 67 74 minecraft:stone
summon minecraft:item_frame 17 67 73 {Facing:2b,Item:{id:"minecraft:filled_map",count:1,components:{"minecraft:map_id":2}}}
"""
    (pack / "data" / "p177" / "function" / "load.mcfunction").write_text(function, encoding="utf-8")


def prepare() -> dict:
    info = p175.prepare(out_world=EDGE_WORLD, instance=INSTANCE)
    uid = uuid.UUID(bytes=hashlib.md5(("OfflinePlayer:" + USERNAME).encode()).digest(), version=3)
    write_map2(EDGE_WORLD / "data" / "map_2.dat")
    write_playerdata(EDGE_WORLD / "playerdata" / f"{uid}.dat")
    write_datapack(EDGE_WORLD)
    return {
        **info,
        "world": str(EDGE_WORLD),
        "maps": [1, 2],
        "frame": {"pos": [17, 67, 73], "facing": 2, "support": [17, 67, 74]},
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
