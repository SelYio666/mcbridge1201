"""Verdict for p212: one panel click installs a version PCL2 actually lists, on a rebuilt shortcut (p212).

The chain has four links and each one is checked against its own artifact, because a screenshot of
a version list proves nothing about who wrote it:

1. **Launcher found** - the desktop shortcut was rebuilt to the launcher that exists
   (`shortcut.json`), and the p211 detector resolves it *through the shortcut* (not the fallback).
2. **Clean start** - the 1.20.4 the previous attempt installed was removed, recorded
   (`clean-state.json`), so `before` in the install run only holds the pre-existing 1.21.1.
3. **Panel install** - the panel's own button command ran against the real game folder
   (`install.json`): version folder, profile, the launcher's asset/library steps, and the real
   Mojang files on disk verified here again by hashing them.
4. **Launcher agrees** - PCL2 (now 2.99.0.0, updated from the snapshot zip over 2.13.1.1) starts,
   its window is grabbed, 版本选择 is clicked, and the list is captured (`pcl2-open.json` +
   `pcl2-click-2.png`). The two screenshots must differ, so "the list was opened" is not just a
   claim about the first frame.

Usage:
  python runs/p212-pcl2-e2e/verify_e2e.py
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
GAME = Path.home() / "AppData" / "Roaming" / ".minecraft"
VERSION = "1.20.4"
CLIENT_BYTES = 24445539
JSON_BYTES = 49394

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (("  " + detail) if detail else ""))


def load(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pixels_differ(a: Path, b: Path) -> tuple[bool, float]:
    from PIL import Image, ImageChops

    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return True, 1.0
    diff = ImageChops.difference(ia, ib)
    total = ia.size[0] * ia.size[1]
    hist = diff.convert("L").histogram()
    changed = total - hist[0]
    return changed > total * 0.01, changed / total


def main() -> int:
    needed = ["shortcut.json", "clean-state.json", "install.json", "launcher-update.json",
              "pcl2-open.json", "desktop-shortcut-before.lnk", "panel-before-install.png",
              "panel-after-install.png", "pcl2-window.png", "pcl2-click-2.png"]
    missing = [n for n in needed if not (RUN / n).is_file()]
    check("every evidence file exists", not missing, ", ".join(missing))
    if missing:
        return 1

    # --- 1. launcher found through the rebuilt shortcut -----------------------
    sc = load("shortcut.json")
    check("shortcut_points_at_the_launcher", sc["after"]["points_at_the_launcher"] is True,
          sc["after"].get("target") or "")
    check("the_broken_shortcut_is_recorded_before_it_was_replaced",
          "涟漪专用启动器" in (sc["before"].get("target") or ""), sc["before"].get("target") or "")
    check("the_old_shortcut_bytes_are_kept",
          sha256(RUN / "desktop-shortcut-before.lnk") == sc["before"]["lnk_sha256"], "")
    check("the_detector_resolves_through_the_shortcut_now",
          sc.get("pcl2_from_desktop") is not None
          and Path(sc["pcl2_from_desktop"]).resolve() == Path(sc["detect_pcl_root"]).resolve(),
          f'{sc.get("pcl2_from_desktop")}')

    # --- 2. clean start ------------------------------------------------------
    clean = load("clean-state.json")
    check("the_previous_attempt_was_removed_and_recorded",
          clean["version_dir_removed"] is not None and clean["profile_removed"] is not None,
          f'files={list((clean["version_dir_removed"] or {}).get("files", {}))}')
    check("nothing_of_it_was_left_behind", clean["version_dir_exists_after"] is False
          and clean.get("profile_keys_after") == ["PCL"],
          f'{clean.get("profile_keys_after")}')

    # --- 3. the panel install ------------------------------------------------
    inst = load("install.json")
    check("the_panel_reported_success", inst["install_ok"] is True and inst["status"] == "完成",
          f'status={inst["status"]} {inst["seconds"]}s')
    check("before_the_click_the_version_was_not_there",
          inst["before"]["versions"] == ["1.21.1"], str(inst["before"]["versions"]))
    check("after_the_click_the_version_is_there",
          VERSION in inst["after"]["versions"], str(inst["after"]["versions"]))
    check("the_panel_wrote_the_client_and_the_version_json",
          inst["after"]["version_files"].get(f"{VERSION}.jar") == CLIENT_BYTES
          and inst["after"]["version_files"].get(f"{VERSION}.json") == JSON_BYTES,
          json.dumps(inst["after"]["version_files"]))
    check("the_panel_added_a_launcher_profile",
          inst["after"]["profile_for_version"]["lastVersionId"] == VERSION
          and inst["after"]["profile_for_version"]["name"] == f"{VERSION} (mcbridge)",
          inst["after"]["profile_for_version"]["name"])
    # What the panel itself records: phase lines in `progress` (status bar) and the per-200 asset
    # counts in the log widget. `install()`'s own "[x/5]" lines go to stdout, which the panel does
    # not capture - checking for them here would be checking the console, not the UI.
    check("the_panel_walked_the_launcher_steps",
          any(p.startswith("client") for p in inst["progress"])
          and any(p.startswith("assets") for p in inst["progress"])
          and any("个已通过校验" in line for line in inst["log_tail"]),
          str(inst["progress"][:3]))
    check("the_only_stubbed_thing_is_the_modal_dialog",
          [d["kind"] for d in inst["dialogs"]] == ["info"], str(inst["dialogs"]))
    check("the_panel_screenshots_show_the_progress_state",
          (RUN / "panel-after-install.png").stat().st_size > 5000
          and pixels_differ(RUN / "panel-before-install.png",
                            RUN / "panel-after-install.png")[0], "")

    # --- the files on disk right now ----------------------------------------
    vdir = GAME / "versions" / VERSION
    check("the_version_folder_is_on_disk", vdir.is_dir(), str(vdir))
    if vdir.is_dir():
        jar = vdir / f"{VERSION}.json"
        data = json.loads(jar.read_text(encoding="utf-8"))
        check("the_version_json_is_a_real_mojang_manifest",
              data.get("id") == VERSION and data.get("assetIndex", {}).get("id") == "12",
              f'id={data.get("id")} assets={data.get("assetIndex", {}).get("id")}')
        jar_bin = vdir / f"{VERSION}.jar"
        check("the_client_jar_matches_the_manifest_hash",
              jar_bin.is_file() and hashlib.sha1(jar_bin.read_bytes()).hexdigest()
              == data["downloads"]["client"]["sha1"], f"{jar_bin.stat().st_size} bytes"
              if jar_bin.is_file() else "missing")
    profiles = json.loads((GAME / "launcher_profiles.json").read_text(encoding="utf-8"))
    check("the_profile_survives_on_disk",
          f"mcbridge-{VERSION}" in (profiles.get("profiles") or {}), "")

    # --- 4. the launcher itself ---------------------------------------------
    upd = load("launcher-update.json")
    check("the_launcher_was_updated_from_the_snapshot_zip",
          upd["before"]["info"]["file_version"] == "2.13.1.1"
          and upd["after"]["info"]["file_version"] == "2.99.0.0", "")
    check("the_extracted_exe_is_the_zip_member_byte_for_byte",
          upd["extracted_matches_zip"] is True and upd["after"]["sha256"] == upd["member"]["sha256"],
          upd["after"]["sha256"][:16] + "…")
    check("the_old_launcher_is_kept_as_a_rollback",
          Path(upd["backup"]["path"]).is_file()
          and upd["backup"]["sha256"] == upd["before"]["sha256"], upd["backup"]["path"])
    check("the_update_kept_the_launcher_settings",
          upd["setup_ini_still_there"] is True and upd["launch_folder_select"]
          and Path(upd["launch_folder_select"].rstrip("\\/")).resolve() == GAME.resolve(),
          upd.get("launch_folder_select") or "")
    check("the_shortcut_still_resolves_after_the_update",
          upd.get("pcl2_from_desktop") is not None, str(upd.get("pcl2_from_desktop")))

    opened = load("pcl2-open.json")
    check("pcl2_started_and_showed_a_window",
          opened["window_found"] is True
          and (opened.get("window_title") or "").startswith("Plain Craft Launcher"),
          opened.get("window_title") or "")
    check("the_window_was_grabbed", (RUN / "pcl2-window.png").stat().st_size > 5000,
          f'{(RUN / "pcl2-window.png").stat().st_size} bytes')
    check("version_selection_was_clicked_and_captured",
          len(opened.get("clicks") or []) == 2
          and Path(opened["clicks"][-1]["shot"]).is_file(), str(opened.get("clicks")))
    differs, ratio = pixels_differ(RUN / "pcl2-window.png", RUN / "pcl2-click-2.png")
    check("the_version_page_is_a_different_frame", differs, f"{ratio:.1%} of pixels changed")
    check("the_launcher_was_closed_again", opened.get("terminated") is True, "")

    verdict = {
        "shortcut": sc,
        "clean": clean,
        "install": {"status": inst["status"], "seconds": inst["seconds"],
                    "before": inst["before"]["versions"], "after": inst["after"]["versions"],
                    "files": inst["after"]["version_files"],
                    "profile": inst["after"]["profile_for_version"],
                    "dialogs": inst["dialogs"]},
        "launcher": {"before": upd["before"]["info"], "after": upd["after"]["info"],
                     "zip_sha256": upd["zip_sha256"], "exe_sha256": upd["after"]["sha256"]},
        "pcl2": {"title": opened.get("window_title"), "clicks": opened.get("clicks"),
                 "frame_diff": round(ratio, 4)},
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
    }
    (RUN / "e2e-check.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")
    failed = [n for n, ok, _ in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    if failed:
        print("failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
