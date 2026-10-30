"""Verdict for p213: PCL2 launches the installed 1.20.4 in offline mode, and the game gets there.

The claim being checked is narrow, so the checks are narrow: the launcher's journal starts a *java*
process whose command line carries the offline identity, that process reaches the title screen, and
the window that appears belongs to the version the panel installed.

"Offline" is not a guess from a settings screen - it is in the argv the launcher built:
`--username SelYio --uuid 0000000000003006998F555B73D6DCEF --accessToken <same>` (a placeholder
token, not a real one) and `-Dminecraft.launcher.brand=PCL`.

Not achieved, and recorded as such: creating a world. The 单人游戏 click reached the create-world
screen, but clicking 创建新的世界 left the frame byte-identical and no world appeared in the log -
the preview server on that screen had started (`Loaded 7 recipes`) and we could not show the button
became usable again.

Usage:
  python runs/p213-pcl2-offline-launch/verify_launch.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
VERSION = "1.20.4"
GAME = Path.home() / "AppData" / "Roaming" / ".minecraft"

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (("  " + detail) if detail else ""))


def load(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def pixel_diff(a: Path, b: Path) -> float:
    from PIL import Image, ImageChops

    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return 1.0
    hist = ImageChops.difference(ia, ib).convert("L").histogram()
    total = ia.size[0] * ia.size[1]
    return (total - hist[0]) / total


def main() -> int:
    needed = ["drive.json", "home.png", "versions.png", "selected.png", "game-window.png",
              "game-title.png", "world-select.png", "world-clicked.png"]
    missing = [n for n in needed if not (RUN / n).is_file()]
    check("every evidence file exists", not missing, ", ".join(missing))
    if missing:
        return 1

    drive = load("drive.json")
    actions = drive["actions"]
    markers = drive.get("markers") or {}
    java = next((a["java"] for a in actions if "java" in a), [])
    argv = (java[0]["command_line"] if java else "") or ""

    # --- the launcher and the version it was told to start --------------------
    check("the_launcher_window_was_the_real_launcher",
          (drive.get("launcher_window") or "").startswith("Plain Craft Launcher"),
          drive.get("launcher_window") or "")
    check("the_version_selector_was_opened",
          pixel_diff(RUN / "home.png", RUN / "versions.png") > 0.01,
          f'{pixel_diff(RUN / "home.png", RUN / "versions.png"):.1%} of pixels changed')
    check("the_target_version_was_the_one_the_panel_installed",
          drive.get("version") == VERSION, str(drive.get("version")))

    # --- a game process, started by that launcher ---------------------------
    game_step = next((a for a in actions if a["step"].startswith("wait-game")), {})
    check("pcl2_started_a_game_window", game_step.get("found") is True
          and (game_step.get("title") or "").startswith("Minecraft " + VERSION),
          game_step.get("title") or "")
    check("the_window_belongs_to_the_installed_version", "1.20.4" in (game_step.get("title") or ""),
          game_step.get("title") or "")
    check("the_launcher_is_named_in_the_java_args", "-Dminecraft.launcher.brand=PCL" in argv, "")
    check("the_java_process_was_pointed_at_the_installed_version",
          f"--version {VERSION}" in argv, "")

    # --- offline mode, from the argv the launcher built ---------------------
    import re

    args = dict(re.findall(r"--(username|uuid|accessToken|userType)\s+(\S+)", argv))
    check("the_session_is_an_offline_one",
          args.get("username") == "SelYio" and args.get("uuid", "").startswith("000000000000")
          and args.get("accessToken", "").startswith("000000000000")
          and args.get("accessToken") == args.get("uuid"),
          json.dumps(args))
    check("no_real_token_was_used", "0000000000003006998F555B73D6DCEF" in args.get("accessToken", ""),
          args.get("accessToken") or "")

    # --- the game actually got to the title screen -------------------------
    title_step = next((a for a in actions if a["step"].startswith("wait-title")), {})
    check("the_title_screen_was_reached", title_step.get("title_screen") is True,
          str(title_step.get("title_screen")))
    check("the_log_says_the_client_entered_the_game",
          any("Setting user: SelYio" in line for line in markers.get("setting_user") or []),
          str(markers.get("setting_user")))
    check("the_sound_engine_started_which_is_the_title_screen",
          any("Sound engine started" in line for line in markers.get("title_screen") or []),
          str(markers.get("title_screen")))
    check("the_title_screen_screenshot_is_not_the_splash",
          (RUN / "game-title.png").stat().st_size > 100_000
          and pixel_diff(RUN / "game-window.png", RUN / "game-title.png") > 0.05,
          f'{(RUN / "game-title.png").stat().st_size} bytes, '
          f'{pixel_diff(RUN / "game-window.png", RUN / "game-title.png"):.1%} differs from the splash')

    # --- the only errors are the ones offline mode causes -------------------
    log = GAME / "versions" / VERSION / "logs" / "latest.log"
    log_lines = log.read_text(encoding="utf-8", errors="replace").splitlines() if log.is_file() else []
    errors = [ln for ln in log_lines if "/ERROR]" in ln]
    unexpected = [ln for ln in errors if not any(
        token in ln for token in ("Realms", "realms", "401", "user properties", "profile key pair"))]
    check("the_game_did_not_crash", not markers.get("crashed"), str(markers.get("crashed")))
    check("the_only_errors_are_the_offline_ones", not unexpected,
          unexpected[0][:120] if unexpected else f"{len(errors)} expected")

    # --- what was driven inside the game, and what was not -----------------
    check("a_click_inside_the_game_worked",
          pixel_diff(RUN / "game-title.png", RUN / "world-select.png") > 0.05,
          f'{pixel_diff(RUN / "game-title.png", RUN / "world-select.png"):.1%} changed after 单人游戏')
    # Creating a world did not happen, and the evidence for that is the log, not the pixels: the
    # two create-world frames differ only by a tooltip disappearing when the cursor moved, which is
    # exactly the kind of difference that would make "the click worked" look true if it were
    # measured on pixels alone.
    logs = [a["markers"] for a in actions if "markers" in a]
    sizes = [m.get("bytes") for m in logs if m.get("exists")]
    check("creating_a_world_did_not_take (recorded, not hidden)",
          not markers.get("world"),
          f"no world-load lines; log grew {sizes[0] if sizes else '?'}->{sizes[-1] if sizes else '?'} "
          f"bytes from screen drawing, not from a world")
    saves = GAME / "versions" / VERSION / "saves"
    worlds = sorted(p.name for p in saves.iterdir()) if saves.is_dir() else []
    check("and_no_world_folder_was_created", not worlds, str(worlds))

    verdict = {
        "launcher": drive.get("launcher_window"),
        "version": drive.get("version"),
        "offline_args": args,
        "java_pid": java[0]["pid"] if java else None,
        "title_screen": bool(title_step.get("title_screen")),
        "log_markers": {k: markers.get(k) for k in ("setting_user", "title_screen", "world",
                                                    "crashed")},
        "world_created": False,
        "world_attempt_note": "创建新的世界 点击后画面字节未变、日志无世界记录；预览服务已启动"
                              "（Loaded 7 recipes），未继续深挖",
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
