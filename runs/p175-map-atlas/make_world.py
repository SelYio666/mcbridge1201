#!/usr/bin/env python3
"""Build the p175 map-atlas test world and mods directory.

Creates a copy of the Fabric 1.21.1 server world under the launcher-e2e test instance, adds
``data/map_1.dat`` with a fixed high-contrast pattern, writes an offline playerdata file whose
hotbar slot 0 holds ``minecraft:filled_map`` with ``minecraft:map_id=1`` and selects that slot,
then installs exactly two mods: Fabric API and the patched ImmediatelyFast jar.

Nothing is written outside ``work/`` except the screenshot/log files the runner keeps in
``runs/p175-map-atlas/``.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import shutil
import struct
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_WORLD = ROOT / "work" / "instances" / "fabric-1.21.1-server" / "world"
INSTANCE = ROOT / "work" / "launcher-e2e"
DEST_WORLD = INSTANCE / "saves" / "ColdWorldMap"
MODS = INSTANCE / "mods"
FABRIC_API_CANDIDATES = [
    ROOT / "work" / "instances" / "fabric-1.21.1-server" / "mods" / "fabric-api.jar",
    ROOT / "work" / "instances" / "fabric-1.21.1-server-all-three" / "mods"
    / "fabric-api-0.102.0+1.21.1.jar",
]
PORTED = ROOT / ".build" / "ImmediatelyFast-ported.jar"
USERNAME = "IFMapUser"

TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG, TAG_FLOAT, TAG_DOUBLE = 1, 2, 3, 4, 5, 6
TAG_BYTE_ARRAY, TAG_STRING, TAG_LIST, TAG_COMPOUND, TAG_INT_ARRAY, TAG_LONG_ARRAY = 7, 8, 9, 10, 11, 12


def _string(value: str) -> bytes:
    raw = value.encode("utf-8")
    return struct.pack(">H", len(raw)) + raw


def _payload(tag: int, value) -> bytes:
    if tag == TAG_BYTE:
        return struct.pack(">b", value)
    if tag == TAG_SHORT:
        return struct.pack(">h", value)
    if tag == TAG_INT:
        return struct.pack(">i", value)
    if tag == TAG_LONG:
        return struct.pack(">q", value)
    if tag == TAG_FLOAT:
        return struct.pack(">f", value)
    if tag == TAG_DOUBLE:
        return struct.pack(">d", value)
    if tag == TAG_BYTE_ARRAY:
        return struct.pack(">i", len(value)) + bytes(value)
    if tag == TAG_STRING:
        return _string(value)
    if tag == TAG_LIST:
        element_tag, items = value
        return struct.pack(">bi", element_tag, len(items)) + b"".join(
            _payload(element_tag, item) for item in items)
    if tag == TAG_COMPOUND:
        out = bytearray()
        for name, (child_tag, child) in value.items():
            out += struct.pack(">b", child_tag) + _string(name) + _payload(child_tag, child)
        out += b"\x00"
        return bytes(out)
    if tag == TAG_INT_ARRAY:
        return struct.pack(">i", len(value)) + b"".join(struct.pack(">i", v) for v in value)
    if tag == TAG_LONG_ARRAY:
        return struct.pack(">i", len(value)) + b"".join(struct.pack(">q", v) for v in value)
    raise ValueError(f"unsupported tag {tag}")


def write_nbt(path: Path, root: dict) -> None:
    """Write a gzip-compressed, unnamed root compound."""
    data = struct.pack(">b", TAG_COMPOUND) + _string("") + _payload(TAG_COMPOUND, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Deterministic gzip header (mtime=0) so repeated runs produce the same bytes.
    with path.open("wb") as raw:
        gz = gzip.GzipFile(fileobj=raw, mode="wb", mtime=0)
        gz.write(data)
        gz.close()


# MapColor ids are stored as (id << 2) | shade in MapState.field_122.
RED = (28 << 2)
BLUE = (25 << 2)
GREEN = (27 << 2)
WHITE = (8 << 2)
BLACK = (29 << 2)
YELLOW = (18 << 2)
GRAY = (3 << 2)


def map_colors() -> bytes:
    """128x128 checkerboard with a black border and a yellow diagonal."""
    data = bytearray(128 * 128)
    for z in range(128):
        for x in range(128):
            if x < 8 or x >= 120 or z < 8 or z >= 120:
                color = BLACK
            elif abs(x - z) < 5:
                color = YELLOW
            else:
                block = ((x - 8) // 16 + (z - 8) // 16) & 1
                if block:
                    color = RED if ((x // 16 + z // 16) & 2) == 0 else BLUE
                else:
                    color = WHITE if ((x // 16 + z // 16) & 2) == 0 else GREEN
            data[x + z * 128] = color
    return bytes(data)


def write_map_state(path: Path) -> None:
    # SavedData files are wrapped: the loader passes nbt.getCompound("data") to MapState.fromNbt
    # (class_26.method_120 in 1.21.1), so the MapState fields must live under "data".
    state = {
        "dimension": (TAG_STRING, "minecraft:overworld"),
        "xCenter": (TAG_INT, 0),
        "zCenter": (TAG_INT, 0),
        "scale": (TAG_BYTE, 0),
        "colors": (TAG_BYTE_ARRAY, map_colors()),
        "trackingPosition": (TAG_BYTE, 1),
        "unlimitedTracking": (TAG_BYTE, 0),
        "locked": (TAG_BYTE, 1),
        "banners": (TAG_LIST, (TAG_COMPOUND, [])),
        "frames": (TAG_LIST, (TAG_COMPOUND, [])),
    }
    root = {
        "DataVersion": (TAG_INT, 3955),
        "data": (TAG_COMPOUND, state),
    }
    write_nbt(path, root)


def write_playerdata(path: Path) -> None:
    map_item = {
        "Slot": (TAG_BYTE, 0),
        "id": (TAG_STRING, "minecraft:filled_map"),
        "count": (TAG_INT, 1),
        "components": (TAG_COMPOUND, {
            "minecraft:map_id": (TAG_INT, 1),
        }),
    }
    root = {
        "DataVersion": (TAG_INT, 3955),
        "Dimension": (TAG_STRING, "minecraft:overworld"),
        # Same spawn as the p139 run (the world's spawn point); a playerdata without Pos is
        # placed at 0,0,0, which is dark/void in this test world.
        "Pos": (TAG_LIST, (TAG_DOUBLE, [17.5, 66.0, 70.5])),
        "Motion": (TAG_LIST, (TAG_DOUBLE, [0.0, 0.0, 0.0])),
        "playerGameType": (TAG_INT, 1),  # creative: no fall damage, no need to move
        "SelectedItemSlot": (TAG_INT, 0),
        "Inventory": (TAG_LIST, (TAG_COMPOUND, [map_item])),
        "Health": (TAG_FLOAT, 20.0),
        "foodLevel": (TAG_INT, 20),
        "XpLevel": (TAG_INT, 0),
        "OnGround": (TAG_BYTE, 1),
        "Rotation": (TAG_LIST, (TAG_FLOAT, [0.0, 0.0])),
    }
    write_nbt(path, root)


def prepare(out_world: Path = DEST_WORLD, instance: Path = INSTANCE) -> dict:
    if not SRC_WORLD.exists():
        raise SystemExit(f"source world missing: {SRC_WORLD}")
    fabric_api = next((p for p in FABRIC_API_CANDIDATES if p.exists()), None)
    if fabric_api is None:
        raise SystemExit(f"Fabric API jar missing (tried {FABRIC_API_CANDIDATES})")
    if not PORTED.exists():
        raise SystemExit(f"patched ImmediatelyFast jar missing: {PORTED}")

    if out_world.exists():
        shutil.rmtree(out_world)
    shutil.copytree(SRC_WORLD, out_world)
    (out_world / "session.lock").unlink(missing_ok=True)
    # The copied playerdata is from other test users; keep it, but replace our own file.
    uid = uuid.UUID(bytes=hashlib.md5(
        ("OfflinePlayer:" + USERNAME).encode()).digest(), version=3)
    write_playerdata(out_world / "playerdata" / f"{uid}.dat")
    write_map_state(out_world / "data" / "map_1.dat")

    mods = Path(instance) / "mods"
    mods.mkdir(parents=True, exist_ok=True)
    for old in mods.glob("*.jar"):
        old.unlink()
    shutil.copy2(fabric_api, mods / fabric_api.name)
    shutil.copy2(PORTED, mods / "ImmediatelyFast-ported.jar")

    # A fresh instance has no options.txt, so 1.21.1 opens the accessibility onboarding screen
    # first and Quick Play waits for a click. Pre-seed the minimum needed for an unattended run.
    options = Path(instance) / "options.txt"
    wanted = {
        "onboardAccessibility": "false",
        "pauseOnLostFocus": "false",
        "narrator": "0",
        "guiScale": "2",
        "renderDistance": "8",
        "simulationDistance": "8",
        "fullscreen": "false",
        "tutorialStep": "none",
    }
    existing: dict[str, str] = {}
    if options.exists():
        for line in options.read_text(encoding="utf-8", errors="replace").splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                existing[key] = value
    existing.update(wanted)
    options.write_text("".join(f"{k}:{v}\n" for k, v in existing.items()), encoding="utf-8")

    return {
        "world": str(out_world),
        "mods": sorted(p.name for p in mods.glob("*.jar")),
        "uuid": str(uid),
        "username": USERNAME,
        "mapId": 1,
        "colors": {
            "red": RED, "blue": BLUE, "green": GREEN, "white": WHITE,
            "black": BLACK, "yellow": YELLOW, "gray": GRAY,
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default=str(DEST_WORLD))
    ap.add_argument("--instance", default=str(INSTANCE))
    args = ap.parse_args(argv)
    try:
        info = prepare(Path(args.world), Path(args.instance))
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for key, value in info.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
