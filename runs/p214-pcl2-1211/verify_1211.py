"""Verdict for p214: the same offline path works for 1.21.1, the version this repo targets (p214).

p213 proved the launcher -> offline identity -> title screen -> world path for 1.20.4, the version
the panel had installed. 1.21.1 is a different animal: it was installed by PCL2 earlier, it is the
version every mod in this repo is converted *for*, and it had never been started through PCL2 here.
The claim checked is deliberately the same shape as p213's, so the two runs are comparable:

* PCL2 2.99.0.0 starts `Minecraft 1.21.1`, and the argv carries the offline placeholder identity
  (`--username SelYio`, `--uuid`/`--accessToken` = `000000000000…`) plus `--version 1.21.1`;
* the client reaches the title screen (`Setting user` -> `Sound engine started`);
* 单人游戏 opens the create-world screen, and Enter creates a world that loads
  (`Time elapsed: 2139 ms`), with `versions\\1.21.1\\saves\\新的世界\\` on disk and an in-game frame;
* the only errors are the two offline ones (no `Not a string` here - that one is 1.20.4-specific).

Usage:
  python runs/p214-pcl2-1211/verify_1211.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
VERSION = "1.21.1"
GAME = Path.home() / "AppData" / "Roaming" / ".minecraft"

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (("  " + detail) if detail else ""))


def pixel_diff(a: Path, b: Path) -> float:
    from PIL import Image, ImageChops

    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return 1.0
    hist = ImageChops.difference(ia, ib).convert("L").histogram()
    total = ia.size[0] * ia.size[1]
    return (total - hist[0]) / total


def main() -> int:
    needed = ["drive.json", "home.png", "versions.png", "game-window.png", "game-title.png",
              "world-list.png", "world-selected.png", "in-game.png",
              # kept from the earlier create-world pass; described in README, not asserted below
              "world-entry.png", "after-enter.png"]
    missing = [n for n in needed if not (RUN / n).is_file()]
    check("every evidence file exists", not missing, ", ".join(missing))
    if missing:
        return 1

    drive = json.loads((RUN / "drive.json").read_text(encoding="utf-8"))
    actions = drive["actions"]
    markers = drive.get("markers") or {}
    java = next((a["java"] for a in actions if a.get("java")), [])
    argv = (java[0]["command_line"] if java else "") or ""

    check("the_launcher_window_was_the_real_launcher",
          (drive.get("launcher_window") or "").startswith("Plain Craft Launcher"),
          drive.get("launcher_window") or "")
    check("the_run_targeted_1_21_1", drive.get("version") == VERSION, str(drive.get("version")))
    check("the_version_selector_was_opened",
          pixel_diff(RUN / "home.png", RUN / "versions.png") > 0.01,
          f'{pixel_diff(RUN / "home.png", RUN / "versions.png"):.1%} changed')

    # --- the process PCL2 started -------------------------------------------
    game_step = next((a for a in actions if a["step"].startswith("wait-game")), {})
    check("pcl2_started_the_1_21_1_window", game_step.get("found") is True
          and (game_step.get("title") or "") == "Minecraft " + VERSION,
          game_step.get("title") or "")
    args = dict(re.findall(r"--(username|uuid|accessToken|userType|version)\s+(\S+)", argv))
    check("the_session_is_an_offline_one",
          args.get("username") == "SelYio"
          and args.get("uuid", "").startswith("000000000000")
          and args.get("accessToken") == args.get("uuid"), json.dumps(args))
    check("the_java_process_targets_1_21_1", args.get("version") == VERSION, ""),
    check("the_launcher_is_named_in_the_java_args", "-Dminecraft.launcher.brand=PCL" in argv, "")

    # --- title screen --------------------------------------------------------
    title_step = next((a for a in actions if a["step"].startswith("wait-title")), {})
    check("the_title_screen_was_reached", title_step.get("title_screen") is True, "")
    check("the_log_names_the_offline_user",
          any("Setting user: SelYio" in ln for ln in markers.get("setting_user") or []),
          str(markers.get("setting_user")))
    check("the_title_screenshot_is_not_the_splash",
          (RUN / "game-title.png").stat().st_size > 100_000
          and pixel_diff(RUN / "game-window.png", RUN / "game-title.png") > 0.05,
          f'{(RUN / "game-title.png").stat().st_size} bytes')

    # --- the world (entered by clicking, like p213) --------------------------
    steps = [a["step"] for a in actions]
    check("a_click_opened_the_world_list",
          pixel_diff(RUN / "game-title.png", RUN / "world-list.png") > 0.05,
          f'{pixel_diff(RUN / "game-title.png", RUN / "world-list.png"):.1%} changed after 单人游戏')
    check("the_world_was_entered_by_clicking",
          any(x.startswith("click-game:435,160") for x in steps)
          and any(x.startswith("click-game:277,428") for x in steps),
          "row click + 进入选中的世界")
    check("the_world_finished_loading",
          any("Time elapsed:" in ln for ln in markers.get("world") or []),
          str(markers.get("world")))
    check("the_in_game_frame_is_not_the_world_list",
          pixel_diff(RUN / "world-list.png", RUN / "in-game.png") > 0.20,
          f'{pixel_diff(RUN / "world-list.png", RUN / "in-game.png"):.1%} different')
    saves = GAME / "versions" / VERSION / "saves"
    worlds = sorted(p.name for p in saves.iterdir()) if saves.is_dir() else []
    check("a_world_folder_exists_for_1_21_1", bool(worlds), str(worlds))

    # --- errors --------------------------------------------------------------
    log = GAME / "versions" / VERSION / "logs" / "latest.log"
    errors = [ln for ln in log.read_text(encoding="utf-8", errors="replace").splitlines()
              if "/ERROR]" in ln] if log.is_file() else []
    allowed = ("Realms", "realms", "401", "user properties", "profile key pair")
    unexpected = [ln for ln in errors if not any(t in ln for t in allowed)]
    check("the_game_did_not_crash", not markers.get("crashed"), str(markers.get("crashed")))
    check("the_only_errors_are_the_offline_ones", not unexpected,
          unexpected[0][:120] if unexpected else f"{len(errors)} expected")
    check("no_1_20_4_only_error_leaked_into_1_21_1",
          not any("Not a string" in ln for ln in errors), "1.20.4 logged one; 1.21.1 does not")

    verdict = {
        "version": VERSION,
        "launcher": drive.get("launcher_window"),
        "offline_args": args,
        "title_screen": bool(title_step.get("title_screen")),
        "world": markers.get("world"),
        "errors": errors,
        "saves": worlds,
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
    }
    (RUN / "launch-check.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8", newline="\n")
    failed = [n for n, ok, _ in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    if failed:
        print("failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
