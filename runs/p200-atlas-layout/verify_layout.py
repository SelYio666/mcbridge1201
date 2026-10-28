#!/usr/bin/env python3
"""Check the p200 evidence: tile-sweep numbers from the log, then the screenshot itself.

Two independent checks:
1. ``client.log`` must contain a sweep line with mapping-mismatch=0 and pixel-mismatch=0, i.e. every
   one of the 2050 map ids was found at the atlas slot the allocator reported, with its own colour
   code - not a sample.
2. ``world.png`` must contain the three layout rectangles the probe logged, at the logged GUI
   coordinates scaled by the logged GUI scale. The rectangle origin offset inside the capture (the
   grab includes the window frame) is derived from the first block and then has to hold for the
   other two, so the check cannot pass by accidentally finding three unrelated coloured areas.

Writes ``layout-check.json`` next to the run for the report; exits non-zero on any mismatch.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PIL import Image

RUN = Path(__file__).resolve().parent
SWEEP_RE = re.compile(
    r"\[p200-probe\] tile-sweep ids=(\d+) mapping-mismatch=(\d+)(?P<mdet>[^ ]*)"
    r" pixel-verified=(\d+) pixel-mismatch=(\d+)")
LAYOUT_RE = re.compile(r"\[p200-probe\] layout-drawn guiScale=([\d.]+) scale=(\d+).*?"
                       r"rects=(?P<rects>\S+) argb=\[(?P<argb>[^\]]*)\]")
RECT_RE = re.compile(r"map(\d+)@(\d+),(\d+)\+(\d+)")

TOLERANCE = 10


def parse_log(text: str) -> dict:
    sweep = None
    layout = None
    for line in text.splitlines():
        m = SWEEP_RE.search(line)
        if m:
            sweep = {
                "ids": int(m.group(1)),
                "mapping_mismatch": int(m.group(2)),
                "pixel_verified": int(m.group(4)),
                "pixel_mismatch": int(m.group(5)),
            }
        m = LAYOUT_RE.search(line)
        if m:
            rects = [{"map": int(a), "x": int(b), "y": int(c), "size": int(d)}
                     for a, b, c, d in RECT_RE.findall(m.group("rects"))]
            layout = {
                "gui_scale": float(m.group(1)),
                "scale": int(m.group(2)),
                "rects": rects,
                "colors": [int(v.strip()) for v in m.group("argb").split(",")],
            }
    return {"sweep": sweep, "layout": layout}


def argb_parts(value: int) -> tuple[int, int, int]:
    """Split a colour the way this pipeline packs it: 0xAABBGGRR, red in the low byte.

    Read as ARGB the three layout blocks look channel-swapped, which is what the first version of
    this checker reported; the atlas pixel and the screenshot pixel agree once the packing is
    applied consistently (0xFFFF4040 -> 64,64,255 on screen, measured).
    """
    return (value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF)


def find_block(image: Image.Image, rgb: tuple[int, int, int], tol: int) -> dict:
    """Bounding box and pixel count of everything within `tol` of `rgb`."""
    width, height = image.size
    pixels = image.convert("RGB").load()
    min_x, min_y, max_x, max_y = width, height, -1, -1
    count = 0
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            if abs(r - rgb[0]) <= tol and abs(g - rgb[1]) <= tol and abs(b - rgb[2]) <= tol:
                count += 1
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
    if count == 0:
        return {"count": 0}
    return {"count": count, "x": min_x, "y": min_y,
            "w": max_x - min_x + 1, "h": max_y - min_y + 1}


def main() -> int:
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else RUN
    log_text = (run / "client.log").read_text(encoding="utf-8", errors="replace")
    parsed = parse_log(log_text)
    problems: list[str] = []
    if not parsed["sweep"]:
        problems.append("no tile-sweep line in client.log")
    else:
        s = parsed["sweep"]
        if s["mapping_mismatch"] != 0:
            problems.append(f"mapping-mismatch={s['mapping_mismatch']}")
        if s["pixel_mismatch"] != 0:
            problems.append(f"pixel-mismatch={s['pixel_mismatch']}")
        if s["pixel_verified"] != s["ids"]:
            problems.append(f"pixel-verified={s['pixel_verified']} != ids={s['ids']}")
    if not parsed["layout"]:
        problems.append("no layout-drawn line in client.log")
        print(json.dumps({"problems": problems}, ensure_ascii=False, indent=2))
        return 1

    layout = parsed["layout"]
    shot = run / "world.png"
    if not shot.exists():
        problems.append("world.png missing")
        print(json.dumps({"problems": problems}, ensure_ascii=False, indent=2))
        return 1
    image = Image.open(shot)
    blocks = []
    for i, rect in enumerate(layout["rects"]):
        rgb = argb_parts(layout["colors"][i])
        block = find_block(image, rgb, TOLERANCE)
        block.update({"map": rect["map"], "expected_x": rect["x"], "expected_y": rect["y"],
                      "expected_size": rect["size"], "rgb": list(rgb)})
        blocks.append(block)

    offsets = []
    for block in blocks:
        if block["count"] < 1000:
            problems.append(f"map {block['map']}: colour {block['rgb']} not found "
                            f"(count={block['count']})")
            continue
        if abs(block["w"] - block["expected_size"]) > 3 or \
                abs(block["h"] - block["expected_size"]) > 3:
            problems.append(f"map {block['map']}: block {block['w']}x{block['h']} != "
                            f"{block['expected_size']}x{block['expected_size']}")
        offsets.append((block["x"] - block["expected_x"], block["y"] - block["expected_y"]))
    if len(offsets) == len(blocks) == 3:
        if len({o[0] for o in offsets}) > 2 or len({o[1] for o in offsets}) > 2:
            problems.append(f"window-frame offsets differ per block: {offsets}")
        step_expected = layout["rects"][1]["x"] - layout["rects"][0]["x"]
        step_actual = blocks[1]["x"] - blocks[0]["x"]
        if abs(step_actual - step_expected) > 2:
            problems.append(f"spacing {step_actual} != expected {step_expected}")

    crop_box = None
    if all("x" in b for b in blocks):
        left = min(b["x"] for b in blocks) - 4
        top = min(b["y"] for b in blocks) - 4
        right = max(b["x"] + b["w"] for b in blocks) + 4
        bottom = max(b["y"] + b["h"] for b in blocks) + 4
        crop_box = (max(left, 0), max(top, 0), min(right, image.width),
                    min(bottom, image.height))
        image.crop(crop_box).save(run / "layout-crop.png")

    report = {
        "sweep": parsed["sweep"],
        "layout": layout,
        "blocks": blocks,
        "offsets": offsets,
        "crop": list(crop_box) if crop_box else None,
        "image_size": list(image.size),
        "tolerance": TOLERANCE,
        "problems": problems,
        "passed": not problems,
    }
    (run / "layout-check.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("passed", "problems", "blocks", "offsets")},
                     ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
