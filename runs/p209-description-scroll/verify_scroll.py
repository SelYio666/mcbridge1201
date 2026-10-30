"""Verdict for p209: does a real wheel drive the description panel, and does the scrollbar show it?

Nothing here trusts the bridge's claim about itself. Four independent kinds of evidence:

1. **Jars**: the p209 jar must differ from the p207 jar in exactly one class entry, and the shipped
   bridge must carry the new debug fields - while the p207 bridge must not, which is what makes the
   control a control.
2. **The control run** (p207 jar, same window, same notches): the panel scrolls there too, so p209
   adds no behaviour - but its debug line cannot say *when it did not scroll*: the row after a long
   description reports the previous row's max, because the old line only printed after drawing.
3. **The p209 run's logs**: exactly one row is scrollable, the wheel over the panel moves the panel
   and not the mod list, the wheel over the mod list moves the mod list and not the panel.
4. **Pixels**: a scrollbar thumb of the predicted height sits at the panel's right edge, it moves
   down by the amount the scroll amount implies, and the text moves up by the scroll amount.

Usage:
  py -3.12 runs/p209-description-scroll/verify_scroll.py
"""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
SCROLL_JAR = ROOT / "work" / "client" / "modmenu-scroll.jar"
P207_JAR = ROOT / "work" / "client" / "modmenu-description.jar"
BRIDGE_PATH = "top/mcbridge1201/bridge/ModMenuListRenderBridge.class"
JAVAP = (ROOT.parent / ".toolchain" / "jdk" / "bin"
         / ("javap.exe" if (ROOT.parent / ".toolchain" / "jdk" / "bin" / "javap.exe").is_file()
            else "javap"))

# The window bitmap is offset from the client area by (+8, +31) at this window size (p205/p207).
FRAME_OFFSET = (8, 31)
THUMB_LEVEL = 35          # luminance of the thumb; the track sits near 10 and the backdrop near 6
SHIFT_LIMIT = 70

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (("  " + detail) if detail else ""))


def panel_device_box(data: dict) -> tuple[int, int, int, int]:
    bx, by, bw, bh = data["panel"]["box"]
    scale = data["window"]["scale"]
    ox, oy = FRAME_OFFSET
    return (ox + int((bx + 4) * scale), oy + int((by + 2) * scale),
            ox + int((bx + bw - 4) * scale), oy + int((by + bh - 2) * scale))


def thumb_runs(png: Path, box: tuple[int, int, int, int]) -> list[list[int]]:
    """Bright contiguous runs in the 6 px scrollbar column at the panel's right edge."""
    from PIL import Image
    x0, y0, x1, y1 = box
    pixels = Image.open(png).convert("L").load()
    cx1, cx0 = x1 - 2, x1 - 8
    rows = [y for y in range(y0, y1)
            if sum(pixels[x, y] for x in range(cx0, cx1)) / 6 >= THUMB_LEVEL]
    runs: list[list[int]] = []
    for y in rows:
        if runs and y - runs[-1][1] <= 1:
            runs[-1][1] = y
        else:
            runs.append([y, y])
    return runs


def best_shift(first: Path, second: Path, box: tuple[int, int, int, int]) -> dict:
    """Vertical offset that best aligns the two shots over the text area (scrollbar excluded)."""
    from PIL import Image
    x0, y0, x1, y1 = box
    a = Image.open(first).convert("RGB").load()
    b = Image.open(second).convert("RGB").load()
    scores = {}
    for dy in range(-SHIFT_LIMIT, SHIFT_LIMIT + 1):
        total = counted = 0
        for y in range(y0, y1, 2):
            sy = y + dy
            if sy < y0 or sy >= y1:
                continue
            for x in range(x0, x1 - 14, 2):
                ca, cb = a[x, y], b[x, sy]
                total += abs(ca[0] - cb[0]) + abs(ca[1] - cb[1]) + abs(ca[2] - cb[2])
                counted += 3
        scores[dy] = total / max(counted, 1)
    best = min(scores, key=scores.get)
    ranked = sorted(scores.items(), key=lambda kv: kv[1])[:3]
    return {"best_dy": best, "best_score": round(scores[best], 2),
            "runner_up": [ranked[1][0], round(ranked[1][1], 2)] if len(ranked) > 1 else None,
            "zero_score": round(scores[0], 2)}


def main() -> int:
    for need in (SCROLL_JAR, P207_JAR, RUN / "before" / "result.json", RUN / "after" / "result.json"):
        if not need.is_file():
            raise SystemExit(f"missing input: {need}; run build.py and both runs first")
    try:
        from PIL import Image  # noqa: F401
    except ModuleNotFoundError:
        raise SystemExit("Pillow is required: run this with `py -3.12`, not `python`")

    control = json.loads((RUN / "before" / "result.json").read_text(encoding="utf-8"))
    fixed = json.loads((RUN / "after" / "result.json").read_text(encoding="utf-8"))

    # --- 1. jars -------------------------------------------------------------------------------
    with zipfile.ZipFile(SCROLL_JAR) as new, zipfile.ZipFile(P207_JAR) as old:
        new_entries = {n: new.read(n) for n in new.namelist() if not n.endswith("/")}
        old_entries = {n: old.read(n) for n in old.namelist() if not n.endswith("/")}
    changed = sorted(n for n in old_entries if n in new_entries and old_entries[n] != new_entries[n])
    added = sorted(set(new_entries) - set(old_entries))
    check("only_the_bridge_differs_from_the_p207_jar",
          changed == [BRIDGE_PATH] and not added, f"changed={changed} added={added}")
    fresh = new_entries.get(BRIDGE_PATH, b"")
    check("the_shipped_bridge_reports_scroll_and_max",
          b"P207_SCROLL" in fresh and b"scroll=" in fresh and b"max=" in fresh
          and b"drawn=" in fresh and b"view=" in fresh, f"{len(fresh)} bytes")
    check("the_p207_bridge_does_not_report_the_same_fields",
          b"drawn=" not in old_entries.get(BRIDGE_PATH, b"drawn=")
          and b"P207_SCROLL" in old_entries.get(BRIDGE_PATH, b"P207_SCROLL"), "")
    check("the_shipped_bridge_still_filters_its_debug_lines",
          b"mcbridge.listrender.debug" in fresh, "")

    # --- 2. the control (p207 jar, same window and notches) ------------------------------------
    c_desc_before = control["before"]["desc"] or {}
    c_desc_after = control["after_panel_wheel"]["desc"] or {}
    check("control_panel_also_scrolls_the_wheel_already_worked",
          c_desc_before.get("scroll") == 0.0 and (c_desc_after.get("scroll") or 0) > 0,
          f'{c_desc_before.get("scroll")} -> {c_desc_after.get("scroll")}')
    c_scan = control["scan"]
    c_row5 = next(e for e in c_scan if e["row"] == 5)
    c_row6 = next(e for e in c_scan if e["row"] == 6)
    check("control_line_cannot_tell_stale_from_empty",
          c_row6["description_count"] == 0 and c_row6["max"] == c_row5["max"] == 568,
          f'row6 count={c_row6["description_count"]} max={c_row6["max"]} (row5 max={c_row5["max"]})')
    check("control_cannot_measure_the_mod_list_scroll",
          (control["after_panel_wheel"]["mod"] or {}).get("scroll") is None,
          "the p207 line has no scroll= field")

    # --- 3. the p209 run's logs ----------------------------------------------------------------
    scan = fixed["scan"]
    scrollable = [e["row"] for e in scan if e["drawn"]]
    check("exactly_one_row_needs_scrolling", scrollable == [5],
          f'{scrollable} of {[e["row"] for e in scan]}')
    check("that_row_is_long_enough_to_scroll",
          (fixed["chosen"]["max"] or 0) > 0 and fixed["chosen"]["description_count"] >= 50,
          f'max={fixed["chosen"]["max"]} rows={fixed["chosen"]["description_count"]}')
    check("every_other_row_reports_max_zero_instead_of_nothing",
          all(e["max"] == 0 and not e["drawn"] for e in scan if e["row"] != 5),
          str([(e["row"], e["max"], e["drawn"]) for e in scan if e["row"] != 5]))
    check("the_empty_row_is_no_longer_a_stale_copy_of_the_previous_one",
          next(e for e in scan if e["row"] == 6)["max"] == 0, "")
    check("the_panel_wheel_moved_the_panel",
          (fixed["before"]["desc"] or {}).get("scroll") == 0.0
          and (fixed["after_panel_wheel"]["desc"] or {}).get("scroll", 0) > 0,
          f'{(fixed["before"]["desc"] or {}).get("scroll")} -> '
          f'{(fixed["after_panel_wheel"]["desc"] or {}).get("scroll")}')
    check("the_panel_wheel_left_the_mod_list_alone",
          (fixed["before"]["mod"] or {}).get("scroll")
          == (fixed["after_panel_wheel"]["mod"] or {}).get("scroll"),
          f'{(fixed["before"]["mod"] or {}).get("scroll")} -> '
          f'{(fixed["after_panel_wheel"]["mod"] or {}).get("scroll")}')
    check("the_panel_wheel_moved_the_thumb_down",
          fixed["after_panel_wheel"]["desc"]["thumb"] != fixed["before"]["desc"]["thumb"],
          f'{fixed["before"]["desc"]["thumb"]} -> {fixed["after_panel_wheel"]["desc"]["thumb"]}')
    mw = fixed["after_mod_wheel"]
    check("the_mod_list_wheel_moved_the_mod_list",
          (mw["before_mod"] or {}).get("scroll") == 0.0 and (mw["mod"] or {}).get("scroll", 0) > 0,
          f'{(mw["before_mod"] or {}).get("scroll")} -> {(mw["mod"] or {}).get("scroll")}')
    check("the_mod_list_wheel_left_the_panel_alone",
          (mw["before_desc"] or {}).get("scroll") == (mw["desc"] or {}).get("scroll"),
          f'{(mw["before_desc"] or {}).get("scroll")} -> {(mw["desc"] or {}).get("scroll")}')
    check("the_run_recorded_that_the_probe_switches_targets",
          fixed["probe_state_targets"] == [11, 78],
          f'{fixed["probe_state_targets"]} (11 = mod list, 78 = panel)')
    log = (RUN / "after" / "client.log").read_text(encoding="utf-8", errors="replace")
    hard = [line for line in log.splitlines()
            if ("NoSuchMethodError" in line or "NoSuchFieldError" in line
                or "IncompatibleClassChangeError" in line or "VerifyError" in line)
            and ("ModMenuListRenderBridge" in line or "DescriptionListWidget" in line)]
    check("no_linkage_error_from_the_two_new_reflective_reads", not hard,
          hard[0][:120] if hard else "none")

    # --- 4. pixels -----------------------------------------------------------------------------
    box = panel_device_box(fixed)
    before_runs = thumb_runs(RUN / "after" / "scroll-before.png", box)
    after_runs = thumb_runs(RUN / "after" / "scroll-after.png", box)
    check("one_thumb_is_drawn_at_the_panel_edge",
          len(before_runs) == 1 and len(after_runs) == 1,
          f"{before_runs} / {after_runs}")
    if len(before_runs) == 1 and len(after_runs) == 1:
        # trackHeight = view - 4 = 212, visible = 212 / (212 + max), thumb = max(16, round(212*vis))
        view = fixed["before"]["desc"]["view"]
        max_scroll = fixed["before"]["desc"]["max"]
        track = view - 4
        predicted = max(16, round(track * (track / (track + max_scroll))))
        height = before_runs[0][1] - before_runs[0][0] + 1
        check("the_thumb_height_is_what_the_formula_predicts",
              abs(height - 2 * predicted) <= 4, f"{height} device px vs 2*{predicted}")
        moved = after_runs[0][0] - before_runs[0][0]
        scroll_delta = (fixed["after_panel_wheel"]["desc"]["scroll"]
                        - fixed["before"]["desc"]["scroll"])
        # The thumb does not follow the scroll 1:1 - it travels (track - thumb) gui px over the whole
        # scroll range, so a 15 px scroll out of 568 moves it 154 * 15/568 = 4 gui px. The first
        # version of this check assumed 1:1 and failed on a correct drawing.
        travel = track - predicted
        expected_move = round(2 * travel * (scroll_delta / max_scroll))
        check("the_thumb_moves_by_the_scroll_ratio",
              abs(moved - expected_move) <= 2,
              f"moved {moved} device px, expected {expected_move} "
              f"({travel} gui px of travel over {max_scroll} of scroll)")
    shift = best_shift(RUN / "after" / "scroll-before.png", RUN / "after" / "scroll-after.png", box)
    expected = round(2 * (fixed["after_panel_wheel"]["desc"]["scroll"]
                          - fixed["before"]["desc"]["scroll"]))
    check("the_text_moves_up_by_the_scroll_amount",
          abs(shift["best_dy"] + expected) <= 4 and shift["best_dy"] != 0,
          f'best_dy={shift["best_dy"]} expected {-expected}')

    c_box = panel_device_box(control)
    c_shift = best_shift(RUN / "before" / "scroll-before.png", RUN / "before" / "scroll-after.png",
                         c_box)
    c_expected = round(2 * (control["after_panel_wheel"]["desc"]["scroll"]
                            - control["before"]["desc"]["scroll"]))
    check("the_control_text_moves_by_its_own_scroll_amount",
          abs(c_shift["best_dy"] + c_expected) <= 4 and c_shift["best_dy"] != 0,
          f'best_dy={c_shift["best_dy"]} expected {-c_expected}')

    verdict = {
        "scroll_jar": str(SCROLL_JAR),
        "control_jar": str(P207_JAR),
        "changed_entries": changed,
        "control": {"scan": c_scan, "before": control["before"],
                    "after_panel_wheel": control["after_panel_wheel"],
                    "shift": c_shift, "panel_box": control["panel"]["box"]},
        "fix": {"scan": scan, "chosen": fixed["chosen"], "panel": fixed["panel"],
                "before": fixed["before"], "after_panel_wheel": fixed["after_panel_wheel"],
                "after_mod_wheel": {k: mw[k] for k in ("mod", "desc")},
                "probe_state_targets": fixed["probe_state_targets"],
                "thumb_before": before_runs, "thumb_after": after_runs,
                "shift": shift, "device_box": list(box)},
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
    }
    (RUN / "scroll-check.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    failed = [n for n, ok, _ in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
