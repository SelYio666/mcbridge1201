"""Verdict for p211: where is PCL2 on this machine, and does our detection see it (and say so)?

Three claims are checked, and none of them is taken from a README:

1. **The environment** - the launcher exists, which version it is, where it is, and which game
   folder its own `PCL/Setup.ini` names. Both probe runs (`before/`, `after/`) must agree, because
   they were taken minutes apart on the same machine.
2. **The defect** - before the fix, the desktop shortcut pointed at a folder that no longer exists,
   the shortcut was skipped without a word, and `detect_pcl_root()` still returned a game folder.
   `before/probe.json` has to show exactly that: no notes, no scan API, `pcl2_from_desktop = None`,
   and a game folder all the same.
3. **The fix** - after it, the same call reports the stale shortcut by name and target, says which
   fallback won, and returns the same folder as before: the fix explains, it does not move anything.
   `panel-smoke.json` shows the note actually rendered in the panel, with a screenshot to look at.

Usage:
  python runs/p211-pcl2-detect/verify_detect.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
PCL2_VERSION = "2.13.1.1"
STALE_TARGET_FRAGMENT = "涟漪专用启动器"

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (("  " + detail) if detail else ""))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    for need in (RUN / "before" / "probe.json", RUN / "after" / "probe.json",
                 RUN / "panel-smoke.json" if (RUN / "panel-smoke.json").is_file()
                 else RUN / "before" / "probe.json"):
        if not need.is_file():
            raise SystemExit(f"missing input: {need}")
    before = load(RUN / "before" / "probe.json")
    after = load(RUN / "after" / "probe.json")
    panel = load(RUN / "panel-smoke.json")

    # --- 1. the environment ---------------------------------------------------
    check("pcl2_exists_on_this_machine", before["exe_exists"] and after["exe_exists"],
          before.get("exe") or "no exe recorded")
    check("pcl2_is_the_version_p137_tested", before["exe_file_version"] == PCL2_VERSION,
          f'{before["exe_file_version"]} / dir name {before["launcher_dir_name"]}')
    check("the_folder_name_disagrees_with_the_exe", before["launcher_dir_name"] is not None
          and "2.12.8.2" in before["launcher_dir_name"]
          and before["exe_file_version"] == "2.13.1.1",
          f'{before["launcher_dir_name"]} vs {before["exe_file_version"]}')
    check("the_launcher_config_names_a_game_folder", bool(before["launch_folder_select"]),
          before.get("launch_folder_select") or "no LaunchFolderSelect")
    check("the_launcher_config_and_the_parser_agree",
          Path(before["launch_folder_select"].rstrip("\\/")).resolve()
          == Path(before["pcl2_game_dir"]).resolve(),
          f'{before["launch_folder_select"]} vs {before["pcl2_game_dir"]}')
    check("the_game_folder_is_real_and_has_versions",
          before["game_dir_exists"] and before["game_dir_versions"],
          f'{before["game_dir_versions"]}')
    check("both_runs_saw_the_same_launcher_bytes",
          before["exe_sha256"] == after["exe_sha256"], before["exe_sha256"][:16] + "…")

    # --- 2. the defect, as it was --------------------------------------------
    shortcut = (before.get("desktop_shortcuts") or [{}])[0]
    check("the_desktop_shortcut_is_on_record", bool(shortcut.get("lnk")),
          shortcut.get("lnk") or "no PCL shortcut found")
    check("its_target_no_longer_exists", shortcut.get("target_exists") is False,
          shortcut.get("target") or "")
    check("the_stale_target_is_the_folder_p137_used",
          STALE_TARGET_FRAGMENT in (shortcut.get("target") or ""), shortcut.get("target") or "")
    check("before_the_fix_the_shortcut_was_the_only_input_and_it_failed",
          before["pcl2_from_desktop"] is None, str(before["pcl2_from_desktop"]))
    check("before_the_fix_nothing_explained_the_miss",
          before["detector_accepts_notes"] is False and before["notes"] == [],
          f'accepts_notes={before["detector_accepts_notes"]} notes={before["notes"]}')
    check("before_the_fix_a_game_folder_came_back_anyway",
          before["detect_pcl_root"] is not None
          and Path(before["detect_pcl_root"]).resolve()
          == Path(before["pcl2_game_dir"]).resolve(),
          before["detect_pcl_root"] or "None")

    # --- 3. the fix ----------------------------------------------------------
    check("after_the_fix_the_call_accepts_notes", after["detector_accepts_notes"] is True, "")
    note_text = " ".join(after.get("notes") or [])
    check("after_the_fix_the_stale_shortcut_is_named",
          "Plain Craft Launcher 2.lnk" in note_text and "已不存在" in note_text, note_text[:120])
    check("after_the_fix_the_dead_target_is_quoted", STALE_TARGET_FRAGMENT in note_text,
          STALE_TARGET_FRAGMENT)
    check("after_the_fix_the_fallback_says_it_is_a_fallback",
          "回退到" in note_text and "AppData" in note_text, note_text[-90:])
    check("the_fix_does_not_move_the_detected_folder",
          after["detect_pcl_root"] == before["detect_pcl_root"],
          f'{before["detect_pcl_root"]} -> {after["detect_pcl_root"]}')
    check("the_shortcut_still_yields_no_game_folder_of_its_own",
          after["shortcut_scan_game_dir"] is None,
          "the launcher is not at the shortcut's target; the fix explains, it does not guess")
    check("the_scan_reports_the_same_single_miss",
          len(after.get("shortcut_scan_notes") or []) == 1,
          str(after.get("shortcut_scan_notes")))

    # --- 4. the panel shows it ----------------------------------------------
    check("the_panel_renders_the_note", panel.get("note_visible") is True
          and "已不存在" in (panel.get("note_label") or ""),
          (panel.get("note_label") or "")[:100])
    check("the_panel_field_still_holds_the_game_folder",
          Path(panel.get("dir_field") or "").resolve()
          == Path(before["pcl2_game_dir"]).resolve(), panel.get("dir_field") or "")
    check("the_panel_loaded_the_version_list", (panel.get("versions_loaded") or 0) > 100,
          f'{panel.get("versions_loaded")} versions')
    shot = panel.get("screenshot")
    check("the_panel_screenshot_exists", bool(shot) and Path(shot).is_file()
          and Path(shot).stat().st_size > 5000,
          f'{Path(shot).stat().st_size} bytes' if shot and Path(shot).is_file() else "none")

    # --- 5. the probe cannot have changed anything ---------------------------
    probe = (RUN / "probe_pcl.py").read_text(encoding="utf-8")
    forbidden = [name for name in ("os.startfile", "install(", "write_launcher_profiles")
                 if re.search(rf"^\s*[^#\n]*{re.escape(name)}", probe, re.M)]
    check("the_probe_is_read_only", not forbidden, f"found: {forbidden}")
    check("the_probe_records_the_path_it_was_given", "given" in before and "given" in after,
          before.get("given") or "")

    verdict = {
        "pcl2": {
            "exe": before.get("exe"),
            "exe_sha256": before.get("exe_sha256"),
            "exe_bytes": before.get("exe_bytes"),
            "file_version": before.get("exe_file_version"),
            "folder_name": before.get("launcher_dir_name"),
            "setup_ini": before.get("setup_ini"),
            "launch_folder_select": before.get("launch_folder_select"),
            "game_dir": before.get("pcl2_game_dir"),
            "game_dir_versions": before.get("game_dir_versions"),
        },
        "shortcut": shortcut,
        "before_notes": before.get("notes"),
        "after_notes": after.get("notes"),
        "panel": panel,
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
    }
    (RUN / "detect-check.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    failed = [n for n, ok, _ in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    if failed:
        print("failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
