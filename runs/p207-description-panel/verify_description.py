"""Verdict for p207: does the description panel now show the selected mod's text?

Nothing here trusts the bridge's own claim. Three independent kinds of evidence:

1. **Bytecode** of the shipped jar: the description render method must still contain the row-building
   calls (so the rows exist) and must not contain a single tombstone reference (so nothing removed
   survives), and the pre-redirect body it was cut from must be byte-identical to the method recorded
   in `runs/p206-modmenu-select/bytecode/render-original.txt`.
2. **Logs**: the two runs differ only in `modmenu.jar`; the panel's entry count must be 0 in the
   control and non-zero in the fix, and the panel's rectangle must be the right-hand one.
3. **Pixels**: inside the panel, the fix run must have several bands of text-coloured pixels and the
   control must not.

Usage:
  python runs/p207-description-panel/verify_description.py
"""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
JDK = ROOT.parent / ".toolchain" / "jdk" / "bin"
JAVAP = JDK / ("javap.exe" if (JDK / "javap.exe").is_file() else "javap")

BUILT = ROOT / "work" / "client" / "modmenu-description.jar"
P206_JAR = ROOT / "work" / "client" / "modmenu-selected.jar"
PRISTINE_JAR = ROOT / "work" / "client" / "modmenu-instrumented.jar"
PANEL_CLASS = "com.terraformersmc.modmenu.gui.widget.DescriptionListWidget"
PANEL_PATH = "com/terraformersmc/modmenu/gui/widget/DescriptionListWidget.class"
RECORDED = ROOT / "runs" / "p206-modmenu-select" / "bytecode" / "render-original.txt"

# Panel interior in window-bitmap pixels: gui (328,108)-(640,324) at scale 2, client area at (8,31).
PANEL_BOX = (668, 251, 1284, 675)
TEXT_MIN = 46
TEXT_MAX = 110
MIN_ROW_PIXELS = 8

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (("  " + detail) if detail else ""))


def javap_method(jar: Path, method: str) -> str:
    out = subprocess.run([str(JAVAP), "-p", "-c", "-cp", str(jar), PANEL_CLASS],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    text = out.stdout
    start = text.find("public void " + method + "(")
    if start < 0:
        return ""
    end = text.find("\n\n", start)
    return text[start:end if end > 0 else len(text)]


def ink_bands(png: Path) -> tuple[int, int, list]:
    from PIL import Image
    im = Image.open(png).convert("L").crop(PANEL_BOX)
    px = im.load()
    width, height = im.size
    rows = [sum(1 for x in range(width) if TEXT_MIN <= px[x, y] <= TEXT_MAX) for y in range(height)]
    bands = []
    start = None
    for y, n in enumerate(rows):
        if n >= MIN_ROW_PIXELS and start is None:
            start = y
        elif n < MIN_ROW_PIXELS and start is not None:
            bands.append([start + PANEL_BOX[1], y + PANEL_BOX[1]])
            start = None
    if start is not None:
        bands.append([start + PANEL_BOX[1], height + PANEL_BOX[1]])
    return len(bands), sum(rows), bands


def main() -> int:
    for need in (BUILT, P206_JAR, PRISTINE_JAR, RECORDED):
        if not need.is_file():
            raise SystemExit(f"missing input: {need}")

    # --- 1. bytecode -------------------------------------------------------
    body = javap_method(BUILT, "method_48579")
    check("description_method_exists", bool(body), f"{len(body.splitlines())} lines of javap")
    check("description_method_keeps_row_building",
          "method_25396" in body and "DescriptionEntry" in body,
          "getEntryList + DescriptionEntry constructions still in the body")
    check("description_method_calls_the_bridge",
          "ModMenuListRenderBridge.renderDescription" in body, "")
    check("description_method_has_no_tombstone_call",
          "Tombstones" not in body, "no centurybridge tombstone reference remains")

    pristine = javap_method(PRISTINE_JAR, "method_48579").strip("\n").splitlines()
    recorded = RECORDED.read_text(encoding="utf-8").splitlines()
    rec_start = next(i for i, line in enumerate(recorded) if "method_48579(" in line)
    rec_end = next(i for i, line in enumerate(recorded) if "renderScrollBar" in line)
    recorded_body = [line.strip() for line in recorded[rec_start:rec_end] if line.strip()]
    pristine_body = [line.strip() for line in pristine if line.strip()]
    # The p206 dump stops at the last tombstone call; the method continues with the scrollbar call
    # and the blend reset. So the record is a prefix of the real body, and that is what is compared.
    same = pristine_body[:len(recorded_body)] == recorded_body
    check("pre_redirect_body_matches_the_p206_record", same,
          f"recorded {len(recorded_body)} lines are the prefix of {len(pristine_body)}")

    with zipfile.ZipFile(BUILT) as new, zipfile.ZipFile(P206_JAR) as old:
        new_entries = {n: new.read(n) for n in new.namelist()}
        old_entries = {n: old.read(n) for n in old.namelist()}
    differing = sorted(n for n in old_entries if n in new_entries and old_entries[n] != new_entries[n])
    added = sorted(set(new_entries) - set(old_entries))
    check("only_the_three_rebuilt_classes_changed",
          differing == sorted([PANEL_PATH,
                               "top/mcbridge1201/bridge/LegacyParentWidget.class",
                               "top/mcbridge1201/bridge/ModMenuListRenderBridge.class"]) and not added,
          ", ".join(differing))

    # --- 2. logs -----------------------------------------------------------
    before = json.loads((RUN / "before" / "result.json").read_text(encoding="utf-8"))
    after = json.loads((RUN / "after" / "result.json").read_text(encoding="utf-8"))
    before_desc = before.get("description") or {}
    after_desc = after.get("description") or {}
    check("control_panel_has_no_rows", before_desc.get("count") == 0,
          f"count={before_desc.get('count')}")
    check("fix_panel_has_rows", (after_desc.get("count") or 0) >= 10,
          f"count={after_desc.get('count')}")
    check("both_runs_selected_the_same_row",
          before["select_after"]["selected"] == 3 and after["select_after"]["selected"] == 3,
          f"{before['select_after']['selected']} / {after['select_after']['selected']}")
    check("mod_list_geometry_unchanged",
          before["mod_list"]["itemHeight"] == after["mod_list"]["itemHeight"] == 36
          and before["mod_list"]["count"] == after["mod_list"]["count"] == 11, "")

    after_log = (RUN / "after" / "client.log").read_text(encoding="utf-8", errors="replace")
    panel_line = re.search(r"P207_PANEL class=DescriptionListWidget box=(-?\d+),(-?\d+),(\d+),(\d+) "
                           r"count=(\d+) legacy=(\w+) rowLeft=(-?\d+)", after_log)
    check("panel_reports_its_real_position", bool(panel_line), panel_line.group(0) if panel_line else
          "no P207_PANEL line")
    if panel_line:
        x, y, w, h = (int(panel_line.group(i)) for i in (1, 2, 3, 4))
        check("panel_sits_in_the_right_half", x == 328 and w == 312 and y == 108 and h == 216,
              f"box={x},{y},{w},{h}")
        check("panel_read_its_layout_from_the_legacy_fields", panel_line.group(6) == "true",
              "legacy=" + panel_line.group(6))

    hard = [line for line in after_log.splitlines()
            if ("NoSuchMethodError" in line or "NoSuchFieldError" in line
                or "IncompatibleClassChangeError" in line or "VerifyError" in line)
            and ("DescriptionListWidget" in line or "ModMenuListRenderBridge" in line
                 or "LegacyParentWidget" in line)]
    check("no_linkage_error_in_the_patched_classes", not hard,
          hard[0][:120] if hard else "none")

    # --- 3. pixels ---------------------------------------------------------
    before_bands, before_ink, _ = ink_bands(RUN / "before" / "sel-after.png")
    after_bands, after_ink, after_list = ink_bands(RUN / "after" / "sel-after.png")
    check("control_panel_has_no_text_bands", before_bands <= 1,
          f"{before_bands} band(s), {before_ink} text-coloured px")
    check("fix_panel_has_text_bands", after_bands >= 5,
          f"{after_bands} band(s), {after_ink} text-coloured px")
    check("fix_panel_ink_dominates_the_control", after_ink > max(1, before_ink) * 5,
          f"{after_ink} vs {before_ink}")

    scroll = re.findall(r"P207_SCROLL[^\n]*", after_log)
    verdict = {
        "built_jar": str(BUILT),
        "control_jar": str(P206_JAR),
        "description_method_lines": len(body.splitlines()),
        "differing_entries": differing,
        "control": {"count": before_desc.get("count"), "bands": before_bands, "ink": before_ink,
                    "description": before_desc},
        "fix": {"count": after_desc.get("count"), "bands": after_bands, "ink": after_ink,
                "bands_y": after_list, "description": after_desc,
                "panel_line": panel_line.group(0) if panel_line else None},
        "scrollbar_lines": scroll,
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
    }
    (RUN / "description-check.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    failed = [n for n, ok, _ in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    if scroll:
        print("scrollbar was drawn:", scroll[-1].strip())
    else:
        print("scrollbar not drawn in this run (maxScroll=0: no description long enough to scroll)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
