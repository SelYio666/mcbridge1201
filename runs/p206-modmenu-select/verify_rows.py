"""Check what the click changed on screen, from the pixels, not from the bridge's own claims.

Vanilla `EntryListWidget.method_44398` draws a 1 px outline around a black interior, which is
practically invisible against this bridge's flat row band, so the bridge also lays a translucent
wash over the selected row. The checker therefore looks for a band of changed pixels that spans the
clicked row (height ~ (rowHeight + 4) * scale) and, in the control jar, for no band at all.

Input: two run directories produced by run.py - `no-highlight` (the p205 jar, which selects rows but
draws no highlight) and `highlight` (this round's jar). Both clicked row 3 at the same device pixel.

Output: highlight-check.json, plus a summary on stdout.

Usage:
  python runs/p206-modmenu-select/verify_rows.py [--out runs/p206-modmenu-select/highlight-check.json]
"""
import argparse
import json
from pathlib import Path

from PIL import Image

RUN = Path(__file__).resolve().parent
SCALE_GUESS = 2.0


def shots(run_dir: Path) -> tuple[Image.Image, Image.Image]:
    return (Image.open(run_dir / "sel-before.png").convert("RGB"),
            Image.open(run_dir / "sel-after.png").convert("RGB"))


def diff_rows(before: Image.Image, after: Image.Image, box: tuple[int, int, int, int],
              threshold: int = 12) -> tuple[list, list, int]:
    """Split the difference into "got brighter" and "got darker" per row.

    The click moves the selection from row 0 to row 3, so a symmetric difference reports two bands -
    the row that lost the highlight and the row that gained it. Splitting by sign lets the checks talk
    about each of them by name instead of guessing which band is which.
    """
    x0, y0, x1, y1 = box
    a, b = before.load(), after.load()
    brighter, darker = [], []
    changed = 0
    for y in range(y0, y1):
        up = down = 0
        for x in range(x0, x1, 2):
            pa, pb = a[x, y], b[x, y]
            da = sum(pb) - sum(pa)
            if max(abs(pa[0] - pb[0]), abs(pa[1] - pb[1]), abs(pa[2] - pb[2])) > threshold:
                changed += 1
                if da > 0:
                    up += 1
                else:
                    down += 1
        brighter.append((y, up))
        darker.append((y, down))
    return brighter, darker, changed


def bands(rows: list[tuple[int, int]], minimum: int) -> list[tuple[int, int]]:
    """Merge adjacent rows whose change count reaches `minimum` into [start, end] bands."""
    out: list[list[int]] = []
    for y, n in rows:
        if n < minimum:
            continue
        if out and y - out[-1][1] <= 2:
            out[-1][1] = y
        else:
            out.append([y, y])
    return [(a, b) for a, b in out]


def analyse(run_dir: Path) -> dict:
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    before, after = shots(run_dir)
    shot_w, shot_h = before.size
    client_w = result["window"]["client_w"]
    client_h = result["window"]["client_h"]
    scale = result["window"]["scale"]
    x_off = (shot_w - client_w) // 2
    y_off = shot_h - client_h - x_off  # bottom and side borders match, the rest is the title bar

    gui = result["probe_list"]["gui"]
    item = result["mod_list"]["itemHeight"]
    x0 = x_off + int(gui[0] * scale)
    x1 = x_off + int((gui[0] + gui[2]) * scale)
    y0 = y_off + int(gui[1] * scale)
    y1 = y_off + int((gui[1] + gui[3]) * scale)

    brighter, darker, changed = diff_rows(before, after, (x0, y0, x1, y1))
    minimum = int((x1 - x0) * 0.4)
    gained = bands(brighter, minimum)
    lost = bands(darker, minimum)

    row = result["click_row"]
    row_top_gui = gui[1] + row * item
    ring_top = y_off + int((row_top_gui - 2) * scale)
    ring_bottom = y_off + int((row_top_gui + item - 4 + 2) * scale)
    first_top = y_off + int((gui[1] - 2) * scale)
    first_bottom = y_off + int((gui[1] + item - 4 + 2) * scale)

    desc_lines = [ln for ln in result.get("widget_lines", []) if "DescriptionListWidget" in ln]
    desc_counts = []
    for line in desc_lines:
        for token in line.split():
            if token.startswith("count="):
                desc_counts.append(int(token.split("=", 1)[1]))

    return {
        "run": str(run_dir.name),
        "jar_sha256": result["modmenu_sha256"],
        "jar_size": result["modmenu_size"],
        "selection_before": result.get("select_before"),
        "selection_after": result.get("select_after"),
        "click": result["click"],
        "mod_list": result["mod_list"],
        "probe_list": result["probe_list"],
        "geometry": {"shot": [shot_w, shot_h], "client": [client_w, client_h], "scale": scale,
                     "offsets": [x_off, y_off], "list_box_px": [x0, y0, x1, y1],
                     "row_top_gui": row_top_gui, "predicted_ring": [ring_top, ring_bottom]},
        "changed_pixels": changed,
        "gained": [[a, b] for a, b in gained],
        "lost": [[a, b] for a, b in lost],
        "first_row_band": [first_top, first_bottom],
        "description_lines": desc_lines,
        "description_counts": desc_counts,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RUN / "highlight-check.json"))
    args = ap.parse_args()

    control = analyse(RUN / "no-highlight")
    fixed = analyse(RUN / "highlight")

    predicted_height = fixed["geometry"]["predicted_ring"][1] - fixed["geometry"]["predicted_ring"][0]
    predicted_centre = (fixed["geometry"]["predicted_ring"][0]
                        + fixed["geometry"]["predicted_ring"][1]) / 2
    first_centre = (fixed["first_row_band"][0] + fixed["first_row_band"][1]) / 2

    def single(bands_list):
        return bands_list[0] if len(bands_list) == 1 else None

    gained = single(fixed["gained"])
    lost = single(fixed["lost"])
    gained_height = (gained[1] - gained[0] + 1) if gained else None
    gained_centre = ((gained[0] + gained[1]) / 2) if gained else None
    lost_centre = ((lost[0] + lost[1]) / 2) if lost else None

    checks = {
        "control_draws_no_selection": not control["gained"] and not control["lost"],
        "fix_changes_more_than_control":
            fixed["changed_pixels"] > 3 * max(control["changed_pixels"], 1),
        "fix_gains_exactly_one_band": len(fixed["gained"]) == 1,
        "fix_loses_exactly_one_band": len(fixed["lost"]) == 1,
        "gained_band_height_matches_the_row":
            gained_height is not None and abs(gained_height - predicted_height) <= 16,
        "gained_band_sits_on_the_clicked_row":
            gained_centre is not None and abs(gained_centre - predicted_centre) <= 12,
        "lost_band_sits_on_the_previously_selected_row":
            lost_centre is not None and abs(lost_centre - first_centre) <= 12,
        "fix_selection_moved_to_the_clicked_row":
            (fixed["selection_before"] or {}).get("selected") == 0
            and (fixed["selection_after"] or {}).get("selected") == fixed["click"]["row"],
        "fix_list_took_focus":
            (fixed["selection_before"] or {}).get("focused") is False
            and (fixed["selection_after"] or {}).get("focused") is True,
        # Not a bug this round fixes: the description list never gets entries because the entry
        # building lives in the render body the redirect replaced. Recorded so the claim stays exact.
        "description_panel_is_empty_in_both_runs":
            all(c == 0 for c in fixed["description_counts"] + control["description_counts"])
            and bool(fixed["description_counts"]),
    }

    report = {"predicted_band_height": predicted_height, "gained_band_height": gained_height,
              "predicted_band_centre": predicted_centre, "gained_band_centre": gained_centre,
              "first_row_band_centre": first_centre, "lost_band_centre": lost_centre,
              "checks": checks, "control": control, "fix": fixed,
              "passed": all(checks.values()), "failed": [k for k, v in checks.items() if not v]}
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8", newline="\n")

    for name, value in checks.items():
        print(("PASS " if value else "FAIL ") + name)
    print(f"control: changed={control['changed_pixels']} gained={control['gained']} "
          f"lost={control['lost']}")
    print(f"fix:     changed={fixed['changed_pixels']} gained={fixed['gained']} lost={fixed['lost']}")
    print(f"         gained centre={gained_centre} (predict {predicted_centre}), "
          f"height={gained_height} (predict {predicted_height}); "
          f"lost centre={lost_centre} (predict {first_centre})")
    print("all checks passed" if report["passed"] else "FAILED: " + ", ".join(report["failed"]))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
