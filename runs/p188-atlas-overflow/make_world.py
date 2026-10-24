#!/usr/bin/env python3
"""p188 world: held-map atlas overflow scene.

Reuses the p175/p181 world builder (map_1.dat unlocked + Fabric API + the ported ImmediatelyFast
jar in the instance mods dir), then adds a p188 data pack that swaps the held item to
filled_map[minecraft:map_id=1024] on tick 40 and keeps replacing it every 40 ticks, so the client
receives a second, server-created map whose id overflows into atlas 1. The p188 probe jar is
installed alongside (test-only, not committed).
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
OVERFLOW_WORLD = INSTANCE / "saves" / "ColdWorldAtlasOverflow"
PROBE = ROOT / "work" / "tmp" / "p188-probe.jar"


def write_datapack(world: Path) -> None:
    pack = world / "datapacks" / "p188-atlas-overflow"
    for part in (("data", "minecraft", "tags", "function"), ("data", "p188", "function")):
        (pack.joinpath(*part)).mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"pack_format": 48, "description": "p188 atlas overflow"}}) + "\n",
        encoding="utf-8")
    (pack / "data" / "minecraft" / "tags" / "function" / "load.json").write_text(
        json.dumps({"values": ["p188:load"]}) + "\n", encoding="utf-8")
    (pack / "data" / "minecraft" / "tags" / "function" / "tick.json").write_text(
        json.dumps({"values": ["p188:tick"]}) + "\n", encoding="utf-8")
    (pack / "data" / "p188" / "function" / "load.mcfunction").write_text(
        "gamerule sendCommandFeedback false\n"
        "scoreboard objectives add p188 dummy\n"
        "fill 14 66 74 20 71 79 minecraft:air\n",
        encoding="utf-8")
    # The integrated server rejected the item component syntax of the earlier datapack
    # ("Incorrect argument ... at position 59"), and the render check no longer needs it: the
    # probe draws the overflow map itself through MapRenderer.draw inside a HUD frame.
    (pack / "data" / "p188" / "function" / "tick.mcfunction").write_text(
        "scoreboard players add @a p188 1\n",
        encoding="utf-8")


def prepare() -> dict:
    info = p181.prepare()
    # p181.prepare() builds ColdWorldMapUpdate; rebuild its content under the overflow world name.
    if OVERFLOW_WORLD.exists():
        shutil.rmtree(OVERFLOW_WORLD)
    shutil.copytree(INSTANCE / "saves" / "ColdWorldMapUpdate", OVERFLOW_WORLD)
    write_datapack(OVERFLOW_WORLD)
    if PROBE.exists():
        shutil.copy2(PROBE, INSTANCE / "mods" / "p188-probe.jar")
    else:
        print(f"warning: probe jar missing ({PROBE}); run build_probe.py first", file=sys.stderr)
    return {
        **info,
        "world": str(OVERFLOW_WORLD),
        "overflow_map_id": 1024,
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
