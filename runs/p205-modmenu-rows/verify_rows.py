"""Measure whether the Mod Menu list actually paints rows, from the committed screenshots.

Two runs are compared: the same client, same mods, same window, same cursor position; the only
difference is the bridge inside `modmenu.jar`. For each run the script measures, inside the list
rectangle only (the scrollbar column is excluded):

  bright      pixels brighter than 90/255          - row text
  saturated   pixels whose channels differ by >25  - mod icons
  bands       horizontal strips with a run of text - how many rows carry content
  shift       vertical offset that best aligns the pre-scroll and post-scroll shot

Usage:
  python runs/p205-modmenu-rows/verify_rows.py
"""
import argparse
import json
from pathlib import Path

from PIL import Image

RUN = Path(__file__).resolve().parent
BRIGHT = 90
SATURATED = 25


def geometry(run_dir: Path) -> tuple[dict, tuple[int, int, int, int], tuple[int, int]]:
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    lx, ly, lw, lh = result["list"]["gui"]
    client_w = result["window"]["client_w"]
    client_h = result["window"]["client_h"]
    scale = result["window"]["scale"]
    return result, (lx, ly, lw, lh), (client_w, client_h)


def frame_offset(image: Image.Image, client: tuple[int, int]) -> tuple[int, int]:
    width, height = image.size
    client_w, client_h = client
    left = (width - client_w) // 2
    top = height - client_h - left
    return left, top


def list_box(image: Image.Image, run_dir: Path) -> tuple[int, int, int, int]:
    """Device-pixel box of the list interior: rows only, scrollbar excluded."""
    result, (lx, ly, lw, lh), client = geometry(run_dir)
    scale = result["window"]["scale"]
    fx, fy = frame_offset(image, client)
    x0 = fx + int((lx + 4) * scale)
    x1 = fx + int((lx + lw - 14) * scale)
    y0 = fy + int((ly + 2) * scale)
    y1 = fy + int((ly + lh - 2) * scale)
    return x0, y0, x1, y1


def measure(path: Path, run_dir: Path) -> dict:
    image = Image.open(path).convert("RGB")
    x0, y0, x1, y1 = list_box(image, run_dir)
    pixels = image.load()
    bright = 0
    saturated = 0
    rows_with_text = []
    for y in range(y0, y1):
        run = 0
        for x in range(x0, x1):
            r, g, b = pixels[x, y]
            if (r + g + b) / 3 > BRIGHT:
                bright += 1
                run += 1
            if max(r, g, b) - min(r, g, b) > SATURATED:
                saturated += 1
        rows_with_text.append((y, run))
    # Content bands are only indicative: a 36 px row with a 32 px icon leaves a gap small enough
    # that adjacent rows merge, so this number undercounts rows. It is reported, not asserted on.
    qualifying = [y for y, run in rows_with_text if run >= 24]
    bands = []
    for y in qualifying:
        if bands and y - bands[-1][1] <= 2:
            bands[-1][1] = y
        else:
            bands.append([y, y])

    # Icon bands are the honest row counter: the icon squares sit in the left 32 px of each row and
    # are the only saturated thing there, so they separate cleanly at the 36 px row pitch.
    result, (lx, ly, lw, lh), client = geometry(run_dir)
    scale = result["window"]["scale"]
    fx, fy = frame_offset(image, client)
    ix0 = fx + int((lx + 4) * scale)
    ix1 = fx + int((lx + 36) * scale)
    icon_rows = []
    for y in range(y0, y1):
        count = 0
        for x in range(ix0, ix1):
            r, g, b = pixels[x, y]
            if max(r, g, b) - min(r, g, b) > SATURATED:
                count += 1
        if count >= 8:
            icon_rows.append(y)
    icon_bands = []
    for y in icon_rows:
        if icon_bands and y - icon_bands[-1][1] <= 6:
            icon_bands[-1][1] = y
        else:
            icon_bands.append([y, y])
    return {"image": path.name, "box": [x0, y0, x1, y1], "bright": bright,
            "saturated": saturated, "content_bands": len(bands),
            "band_heights": [b - a + 1 for a, b in bands],
            "icon_bands": len(icon_bands),
            "icon_band_heights": [b - a + 1 for a, b in icon_bands],
            "bright_rows": len(qualifying)}


def best_shift(first: Path, second: Path, run_dir: Path, limit: int = 90) -> dict:
    a = Image.open(first).convert("RGB")
    b = Image.open(second).convert("RGB")
    x0, y0, x1, y1 = list_box(a, run_dir)
    pa, pb = a.load(), b.load()
    best = (0, float("inf"))
    scores = {}
    for dy in range(-limit, limit + 1):
        total = 0
        count = 0
        for y in range(y0, y1, 2):
            sy = y + dy
            if sy < y0 or sy >= y1:
                continue
            for x in range(x0, x1, 2):
                ca, cb = pa[x, y], pb[x, sy]
                total += abs(ca[0] - cb[0]) + abs(ca[1] - cb[1]) + abs(ca[2] - cb[2])
                count += 3
        score = total / max(count, 1)
        scores[dy] = round(score, 2)
        if score < best[1]:
            best = (dy, score)
    ranked = sorted(scores.items(), key=lambda kv: kv[1])[:3]
    return {"best_dy": best[0], "best_score": round(best[1], 2),
            "runner_up": ranked[1] if len(ranked) > 1 else None,
            "zero_shift_score": scores.get(0)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RUN / "rows-check.json"))
    args = ap.parse_args()

    report: dict = {}
    for label in ("before", "after"):
        run_dir = RUN / label
        if not (run_dir / "rows-before.png").exists():
            raise SystemExit(f"missing screenshots under {run_dir}")
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        rows_before = measure(run_dir / "rows-before.png", run_dir)
        rows_scrolled = measure(run_dir / "rows-scrolled.png", run_dir)
        shift = best_shift(run_dir / "rows-before.png", run_dir / "rows-scrolled.png", run_dir)
        expected = (result["scroll_after"] - result["scroll_before"]) * result["window"]["scale"]
        report[label] = {
            "modmenu_sha256": result["modmenu_sha256"],
            "scroll": [result["scroll_before"], result["scroll_after"]],
            "expected_device_shift": expected,
            "before_scroll": rows_before,
            "after_scroll": rows_scrolled,
            "shift": shift,
            "p205_lines": result.get("p205_list_lines", []),
            "shift_matches": abs(abs(shift["best_dy"]) - expected) <= 3,
        }

    after = report["after"]["before_scroll"]
    before = report["before"]["before_scroll"]
    checks = {
        "before_draws_no_rows": before["icon_bands"] == 0 and before["bright"] < 400,
        "after_draws_rows": after["icon_bands"] >= 5,
        "after_icons_are_row_sized": sum(1 for h in after["icon_band_heights"]
                                         if 30 <= h <= 90) >= 5,
        "after_has_icons": after["saturated"] > 20 * max(before["saturated"], 1),
        "after_text_far_brighter": after["bright"] > 10 * max(before["bright"], 1),
        "rows_move_with_scroll": report["after"]["shift_matches"]
                                and report["after"]["shift"]["best_dy"] != 0,
        "before_rows_do_not_move": report["before"]["shift"]["best_dy"] == 0
                                   or report["before"]["before_scroll"]["icon_bands"] == 0,
        "debug_line_names_modlistwidget": any("class=ModListWidget" in line
                                              for line in report["after"]["p205_lines"]),
    }
    report["checks"] = checks
    report["passed"] = all(checks.values())
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8", newline="\n")
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    print("before:", json.dumps(before), "shift", report['before']['shift']['best_dy'])
    print("after :", json.dumps(after), "shift", report['after']['shift']['best_dy'],
          "expected", report['after']['expected_device_shift'])
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
