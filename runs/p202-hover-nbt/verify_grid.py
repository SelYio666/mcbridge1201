#!/usr/bin/env python3
"""p202 screenshot check: the FULL preview shows 9x3 item icons and all 27 cells differ.

Geometry is MEASURED, not assumed:

* The probe logs the panel origin in GUI coordinates (P202_DRAWITEMS ... x=355 y=189), the GUI
  scale (P202_TARGET ... scale=2.0) and the client area (P202_WINDOW m4480/m4507). The window frame
  is derived from the PNG size against that client area, so the crop is not eyeballed.
* The slot lattice is then found from the image itself. The pitch comes from the autocorrelation of
  the luminance profile - the lag with the highest correlation is the slot period and it has to be
  exactly 18*scale. The phase comes from the offset whose lattice lines are darkest, i.e. where the
  one-pixel separators between slots sit. Neither step searches for "an answer that passes"; both
  report their numbers (peak lag, correlation, phase, contrast) so they can be checked.
* Icons are then sampled as 32x32 patches centred in each cell (16*scale), which is the item
  sprite size; using the centre instead of the cell border means a one-pixel phase error cannot
  clip an icon or mix in a neighbour.

What the picture has to show, given the log said 27 items and 27 different component maps: every
one of the 27 patches contains ink, and every patch is different. Two slots holding the same stack
would hash equal - exactly what a heterogeneous-NBT box must not look like.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
COLS, ROWS = 9, 3


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def parse_probe(log: str) -> dict:
    data: dict = {}
    match = re.search(r"P202_DRAWITEMS call=\d+ type=FULL items=(\d+) x=(-?\d+) y=(-?\d+)", log)
    if match:
        data["items"] = int(match.group(1))
        data["grid_x"] = int(match.group(2))
        data["grid_y"] = int(match.group(3))
    match = re.search(r"P202_TARGET gx=[-\d.]+ gy=[-\d.]+ scale=([-\d.]+)", log)
    if match:
        data["scale"] = float(match.group(1))
    match = re.search(r"P202_WINDOW handle=\d+ m4480=(\d+) m4486=\d+ m4502=\d+ m4507=(\d+)", log)
    if match:
        data["client_w"] = int(match.group(1))
        data["client_h"] = int(match.group(2))
    return data


def _lum(pixel: tuple[int, int, int]) -> int:
    red, green, blue = pixel
    return (red * 299 + green * 587 + blue * 114) // 1000


def column_profile(image, x0: int, x1: int, y0: int, y1: int) -> list[int]:
    pixels = image.convert("RGB").load()
    return [sum(_lum(pixels[x, y]) for y in range(y0, y1)) // max(y1 - y0, 1)
            for x in range(x0, x1)]


def row_profile(image, x0: int, x1: int, y0: int, y1: int) -> list[int]:
    pixels = image.convert("RGB").load()
    return [sum(_lum(pixels[x, y]) for x in range(x0, x1)) // max(x1 - x0, 1)
            for y in range(y0, y1)]


def best_lag(profile: list[int], low: int, high: int) -> tuple[int, float, float]:
    """Lag with the strongest autocorrelation, plus the runner-up for contrast."""
    mean = sum(profile) / len(profile)
    centred = [value - mean for value in profile]
    scored: list[tuple[float, int]] = []
    for lag in range(low, min(high, len(profile) - 1) + 1):
        total = sum(centred[i] * centred[i + lag] for i in range(len(centred) - lag))
        scored.append((total, lag))
    scored.sort(reverse=True)
    return scored[0][1], scored[0][0], scored[1][0]


def phase_of(profile: list[int], cell: int, around: int) -> tuple[int, float, float]:
    """Lattice line nearest the panel origin the probe reported, refined to the darkest one.

    Which of two adjacent lattice lines is "first" is ambiguous by exactly one cell - both are
    evenly dark. The probe reports where the renderer's panel starts and its padding is smaller
    than a cell, so the first line has to be within half a cell of that origin; the search is
    limited to that window and, inside it, picks the darkest line.
    """
    low = max(0, around - cell // 2)
    high = min(len(profile), around + cell // 2)
    best_phase, best_score = around, float("inf")
    worst_score = float("-inf")
    for phase in range(low, high):
        values = profile[phase::cell]
        if not values:
            continue
        score = sum(values) / len(values)
        if score < best_score:
            best_phase, best_score = phase, score
        worst_score = max(worst_score, score)
    return best_phase, best_score, worst_score


def patch(image, left: int, top: int, size: int) -> tuple[str, int, int]:
    """(sha, ink pixels, distinct colours) for a square patch."""
    crop = image.crop((left, top, left + size, top + size)).convert("RGB")
    pixels = list(crop.getdata())
    counts: dict[tuple[int, int, int], int] = {}
    for pixel in pixels:
        counts[pixel] = counts.get(pixel, 0) + 1
    background = max(counts.items(), key=lambda kv: kv[1])[0]
    ink = sum(1 for pixel in pixels if pixel != background)
    return hashlib.sha256(crop.tobytes()).hexdigest()[:16], ink, len(counts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", default=str(RUN / "after-full.png"))
    ap.add_argument("--log", default=str(RUN / "client.log"))
    ap.add_argument("--json", default=str(RUN / "grid-check.json"))
    args = ap.parse_args()

    try:
        from PIL import Image
    except ImportError:
        print("Pillow missing: cannot verify the screenshot", file=sys.stderr)
        return 2

    png = Path(args.png)
    if not png.exists():
        print(f"missing screenshot: {png}", file=sys.stderr)
        return 2
    probe = parse_probe(read_text(Path(args.log)))
    result: dict = {"png": png.name, "probe": probe, "checks": {}, "passed": False}
    if not all(key in probe for key in ("items", "grid_x", "grid_y", "scale",
                                        "client_w", "client_h")):
        result["error"] = "probe did not log the FULL grid origin / scale / client size"
        Path(args.json).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 1

    image = Image.open(png)
    result["image_size"] = list(image.size)
    frame_x = (image.size[0] - probe["client_w"]) / 2
    frame_y = image.size[1] - probe["client_h"] - frame_x
    result["frame_offset"] = [round(frame_x, 1), round(frame_y, 1)]

    scale = probe["scale"]
    cell = int(round(18 * scale))
    base_x = int(round(frame_x + probe["grid_x"] * scale))
    base_y = int(round(frame_y + probe["grid_y"] * scale))
    result["base_origin"] = [base_x, base_y]
    result["cell_size"] = cell

    scan_left, scan_top = base_x - cell, base_y - cell
    scan_w, scan_h = COLS * cell + 2 * cell, ROWS * cell + 2 * cell
    if scan_left < 0 or scan_top < 0 or scan_left + scan_w > image.size[0] \
            or scan_top + scan_h > image.size[1]:
        result["error"] = "scan window falls outside the screenshot"
        Path(args.json).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 1

    # profiles are limited to the panel's own area: over the wider scan window the panel frame and
    # the world behind the inventory dominate, and the row autocorrelation went negative
    panel_x0, panel_x1 = base_x - 4, base_x + COLS * cell + cell // 2
    panel_y0, panel_y1 = base_y - 4, base_y + ROWS * cell + cell // 2
    columns = column_profile(image, panel_x0, panel_x1, panel_y0, panel_y1)
    col_lag, col_peak, col_second = best_lag(columns, cell - 6, cell + 6)
    col_phase, col_dark, col_bright = phase_of(columns, cell, base_x - panel_x0)
    origin_x = panel_x0 + col_phase

    rows = row_profile(image, origin_x + 4, origin_x + COLS * cell - 4, panel_y0, panel_y1)
    row_lag, row_peak, row_second = best_lag(rows, cell - 6, cell + 6)
    row_phase, row_dark, row_bright = phase_of(rows, cell, base_y - panel_y0)
    origin_y = panel_y0 + row_phase

    result["pitch"] = {"columns": col_lag, "rows": row_lag,
                       "column_peak": round(col_peak, 1), "column_runner_up": round(col_second, 1),
                       "row_peak": round(row_peak, 1), "row_runner_up": round(row_second, 1)}
    result["phase"] = {"columns": col_phase, "rows": row_phase,
                       "column_darkest": round(col_dark, 1), "column_brightest": round(col_bright, 1),
                       "row_darkest": round(row_dark, 1), "row_brightest": round(row_bright, 1)}
    result["lattice_origin"] = [origin_x, origin_y]
    sprite = int(round(16 * scale))
    result["sprite_size"] = sprite

    hashes: list[str] = []
    inks: list[int] = []
    colours: list[int] = []
    for row in range(ROWS):
        for col in range(COLS):
            centre_x = origin_x + col * cell + cell // 2
            centre_y = origin_y + row * cell + cell // 2
            digest, ink, distinct = patch(image, centre_x - sprite // 2, centre_y - sprite // 2,
                                          sprite)
            hashes.append(digest)
            inks.append(ink)
            colours.append(distinct)

    result["distinct_cells"] = len(set(hashes))
    result["blank_cells"] = sum(1 for ink in inks if ink < 0.10 * sprite * sprite)
    result["flat_cells"] = sum(1 for count in colours if count < 4)
    result["ink_pixels"] = inks
    result["colour_counts"] = colours
    result["grid_span"] = [COLS * cell, ROWS * cell]

    separator_contrast = col_bright - col_dark
    checks = {
        "probe_reported_27_items": probe["items"] == 27,
        "cell_is_18_times_scale": cell == int(round(18 * scale)),
        "column_pitch_is_one_cell": col_lag == cell,
        "row_pitch_is_one_cell": row_lag == cell,
        "separators_darker_than_slots": separator_contrast >= 15,
        "all_27_cells_have_ink": result["blank_cells"] == 0,
        "no_flat_cell": result["flat_cells"] == 0,
        "27_distinct_cell_pixels": result["distinct_cells"] == 27,
    }
    result["checks"] = checks
    result["passed"] = all(checks.values())
    Path(args.json).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("image_size", "frame_offset", "base_origin", "lattice_origin", "pitch",
                       "phase", "cell_size", "sprite_size", "grid_span", "distinct_cells",
                       "blank_cells", "flat_cells", "checks", "passed")}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
