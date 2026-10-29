#!/usr/bin/env python3
"""p204 visual check: the scrollbar thumb moved exactly as far as the scroll amount implies.

Why not the rows: in this environment the mod-list rows still do not paint (the area is black in
both p94's committed screenshots and in every p204 shot - recorded as a separate defect). What does
paint is the list's own scrollbar, which EntryListWidget derives from the scroll amount:

    thumb_top = list_top + scroll / max_scroll * (track - thumb_height)

So the thumb is a direct visual read-out of the state the probe logged, and it is measured here
rather than eyeballed:

* the scrollbar column is found by taking, for every column in the list's right strip, the median
  brightness down the list; the thumb column is the brightest one (the track is dark, the thumb is
  a flat ~100 grey);
* the thumb's vertical extent is every row in that column brighter than half-way between the track
  minimum and that median - no fixed threshold, so a different GUI background cannot break it;
* two predictions are checked: one notch (scroll 18 of max 147) must move the thumb by
  18/147 of the free track, and full scroll must put the thumb at the very bottom;
* after the typed filter (11 entries -> 1) max_scroll is 0, so the scrollbar must disappear.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent


def find_thumb(path: Path, list_gui: list[int], scale: float,
               client: tuple[int, int]) -> dict:
    from PIL import Image

    image = Image.open(path).convert("RGB")
    img_w, img_h = image.size
    frame_x = (img_w - client[0]) // 2
    frame_y = img_h - client[1] - frame_x
    lx, ly, lw, lh = list_gui
    x_lo = frame_x + int(round((lx + max(lw - 12, 0)) * scale))
    x_hi = frame_x + int(round((lx + lw) * scale))
    y_lo = frame_y + int(round(ly * scale))
    y_hi = frame_y + int(round((ly + lh) * scale))
    pixels = image.load()

    best = (0.0, x_lo)
    for x in range(x_lo, x_hi):
        values = sorted(sum(pixels[x, y]) / 3 for y in range(y_lo, y_hi, 4))
        median = values[len(values) // 2]
        if median > best[0]:
            best = (median, x)
    median, column = best
    luminance = [(y, sum(pixels[column, y]) / 3) for y in range(y_lo, y_hi)]
    darkest = min(value for _, value in luminance)
    threshold = (darkest + median) / 2
    lit = [y for y, value in luminance if value > threshold]
    has_thumb = median >= 40 and len(lit) >= 8
    return {
        "file": path.name,
        "image_size": [img_w, img_h],
        "frame_offset": [frame_x, frame_y],
        "column": column,
        "column_median": round(median, 1),
        "track_min": round(darkest, 1),
        "has_thumb": has_thumb,
        "thumb": [min(lit), max(lit)] if has_thumb else None,
        "track": [y_lo, y_hi],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RUN / "scroll-check.json"))
    ap.add_argument("--run-dir", default=None,
                    help="check another copy of the run (e.g. a repeat) instead of this directory")
    args = ap.parse_args()
    run_dir = Path(args.run_dir) if args.run_dir else RUN

    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    scale = float(result["window"]["scale"])
    client = (int(result["window"]["client_w"]), int(result["window"]["client_h"]))
    list_gui = result["list"]["gui"]
    maximum = float(result["max_scroll"])
    first = float(result["wheel_steps"][0]["scroll"])

    shots = {name: find_thumb(run_dir / f"{name}.png", list_gui, scale, client)
             for name in ("list-before", "list-scrolled", "list-scrolled-max", "list-filtered")}
    before = shots["list-before"]
    one = shots["list-scrolled"]
    full = shots["list-scrolled-max"]
    filtered = shots["list-filtered"]

    problems: list[str] = []
    if not (before["has_thumb"] and one["has_thumb"] and full["has_thumb"]):
        problems.append("no scrollbar thumb found in one of the scroll screenshots")
    track = (before["track"][1] - before["track"][0]) if before["has_thumb"] else 0
    thumb_h = (before["thumb"][1] - before["thumb"][0]) if before["has_thumb"] else 0
    free = track - thumb_h
    measured_one = (one["thumb"][0] - before["thumb"][0]) if before["has_thumb"] and one["has_thumb"] else None
    measured_full = (full["thumb"][0] - before["thumb"][0]) if before["has_thumb"] and full["has_thumb"] else None
    predicted_one = round(first / maximum * free) if maximum and free else None

    checks = {
        "thumb_found": not problems,
        "thumb_height_stable": all(
            abs((s["thumb"][1] - s["thumb"][0]) - thumb_h) <= 4
            for s in (one, full) if s["has_thumb"] and before["has_thumb"]),
        "one_notch_matches_formula": (measured_one is not None and predicted_one is not None
                                      and abs(measured_one - predicted_one) <= 3),
        "full_scroll_reaches_bottom": (measured_full is not None and free
                                       and abs(measured_full - free) <= 3),
        "thumb_inside_track": bool(before["has_thumb"]
                                   and before["thumb"][0] >= before["track"][0] - 1
                                   and before["thumb"][1] <= before["track"][1] + 1),
        "filter_removes_scrollbar": not filtered["has_thumb"],
    }
    data = {
        "list_gui": list_gui,
        "scale": scale,
        "scroll_one_notch": first,
        "max_scroll": maximum,
        "track_px": track,
        "thumb_px": thumb_h,
        "free_track_px": free,
        "predicted_one_notch_shift": predicted_one,
        "measured_one_notch_shift": measured_one,
        "measured_full_shift": measured_full,
        "shots": shots,
        "checks": checks,
        "problems": problems,
        "passed": all(checks.values()),
    }
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    print(json.dumps({k: data[k] for k in ("track_px", "thumb_px", "free_track_px",
                                           "predicted_one_notch_shift",
                                           "measured_one_notch_shift",
                                           "measured_full_shift", "checks", "problems")},
                     ensure_ascii=False))
    return 0 if data["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
