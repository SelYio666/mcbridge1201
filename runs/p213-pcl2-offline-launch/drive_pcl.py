"""Drive PCL2 by clicking it, then prove the game it starts is on screen (p213).

p212 stopped at "the launcher lists the version". The obvious next question is whether it *launches*
it - and the answer does not need an account: PCL2 is in offline mode (the panel shows 离线 with the
username `SelYio`), so the only things needed are a working install, Java, and a window.

This is a small step list rather than one hard-coded sequence, so the coordinates that worked are
part of the evidence:

    --step "shot:home" --step "click:608,815" --step "sleep:2" --step "shot:versions" \
    --step "click:930,522" --step "sleep:2" --step "shot:selected" \
    --step "click:675,765" --step "wait-game:180" --step "ps" --step "shot:game"

`click` uses screen coordinates (SendInput, absolute); `wait-game` polls for a window whose title
starts with "Minecraft" and grabs it; `ps` records the command line of every java process, which is
where offline mode becomes visible (`--username SelYio --uuid … --accessToken 0`).

Usage:
  python runs/p213-pcl2-offline-launch/drive_pcl.py --exe "<PCL2 exe>" --out runs/p213-pcl2-offline-launch
"""
from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(RUN.parent / "p212-pcl2-e2e"))
import pcl2_open as drv  # noqa: E402  (_click, windows_of, area_of, title_of, _processes_of)
from test_launcher_e2e import _print_window  # noqa: E402

SLEEP_BEFORE_FIRST = 6


def rect_of(hwnd: int) -> list[int]:
    r = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
    return [r.left, r.top, r.right, r.bottom]


def activate(hwnd: int) -> dict:
    """Force the launcher to the front and report whether it actually got there.

    A SendInput click goes to whatever window is foreground at that moment, and Windows ignores a
    bare `SetForegroundWindow` from a background process (p202 hit this first, p204 fixed it with
    `AttachThreadInput`). Without this the click lands on the terminal: the launcher page does not
    change and the run silently "proves" nothing - observed as `foreground: false` with 6 attempts.
    """
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    flags = 0x0001 | 0x0002 | 0x0040  # NOSIZE | NOMOVE | SHOWWINDOW
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    result: dict = {"attempts": 0, "foreground": False}
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, flags)  # HWND_TOPMOST
    result["attempts"] = 1
    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)
    time.sleep(0.4)
    if user32.GetForegroundWindow() == hwnd:
        result["foreground"] = True
    else:
        for attempt in range(4):
            result["attempts"] = attempt + 2
            fg = user32.GetForegroundWindow()
            tid_fg = user32.GetWindowThreadProcessId(fg, None)
            tid_me = kernel32.GetCurrentThreadId()
            attached = user32.AttachThreadInput(tid_me, tid_fg, True)
            user32.SetForegroundWindow(hwnd)
            user32.SetFocus(hwnd)
            user32.AttachThreadInput(tid_me, tid_fg, False)
            result["attached"] = bool(attached)
            time.sleep(0.4)
            if user32.GetForegroundWindow() == hwnd:
                result["foreground"] = True
                break
    user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, flags)  # HWND_NOTOPMOST: do not cover the desktop
    return result


def java_command_lines() -> list[dict]:
    """Every java.exe with its command line (offline mode is visible there)."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"name='java.exe'\" | "
             "Select-Object ProcessId,CommandLine | ConvertTo-Json -Depth 3"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return [{"error": str(exc)}]
    if not out:
        return []
    data = json.loads(out)
    if isinstance(data, dict):
        data = [data]
    return [{"pid": d.get("ProcessId"), "command_line": d.get("CommandLine")} for d in data]


def game_window() -> int | None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):  # noqa: ANN001
        if not user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if buf.value.lower().startswith("minecraft"):
            found.append(hwnd)
        return True

    user32.EnumWindows(_enum, 0)
    if not found:
        return None
    return max(found, key=drv.area_of)


def latest_log_markers(game: Path, version: str | None = None) -> dict:
    """Markers from latest.log.

    PCL runs each version in its own folder by default (`--gameDir <game>/versions/<ver>`), so the
    log is *not* at `<game>/logs/latest.log` on this setup - checking the default path reported
    `exists: false` while the game was sitting on the title screen.
    """
    candidates = []
    if version:
        candidates.append(game / "versions" / version / "logs" / "latest.log")
    candidates.append(game / "logs" / "latest.log")
    log = next((p for p in candidates if p.is_file()), None)
    if log is None:
        return {"exists": False, "looked_at": [str(p) for p in candidates]}
    text = log.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    return {
        "exists": True,
        "path": str(log),
        "bytes": log.stat().st_size,
        "setting_user": [ln for ln in lines if "Setting user:" in ln][-1:],
        "title_screen": [ln for ln in lines if "Sound engine started" in ln][-1:],
        "world": [ln for ln in lines if "Preparing spawn area" in ln
                  or "Loaded 0 advancements" in ln or "Time elapsed:" in ln][-2:],
        "crashed": [ln for ln in lines if "Unhandled exception" in ln
                    or "---- Minecraft Crash" in ln],
        "tail": lines[-6:],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--game", default=str(Path.home() / "AppData" / "Roaming" / ".minecraft"))
    ap.add_argument("--step", action="append", default=[])
    ap.add_argument("--version", default="1.20.4",
                    help="the version PCL2 launches; also where its isolated log lives")
    ap.add_argument("--attach", action="store_true",
                    help="不启动新的 PCL2，直接驱动已经在跑的游戏窗口（用于接着上一轮）")
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    game = Path(args.game)
    exe = Path(args.exe)
    info: dict = {"exe": str(exe), "version": args.version, "steps": args.step,
                  "actions": [], "shots": []}

    hwnd = None
    if args.attach:
        info["attached"] = True
        info["launcher_window"] = None
        gw = game_window()
        if not gw:
            (out / "launch.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8", newline="\n")
            print(json.dumps({"error": "no running game window to attach to"}, ensure_ascii=False))
            return 1
        info["attached_game_title"] = drv.title_of(gw)
        info["attached_game_rect"] = rect_of(gw)
    else:
        for pid in drv._processes_of(exe.name):
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=20)
            info.setdefault("killed_existing", []).append(pid)
        if info.get("killed_existing"):
            time.sleep(3)

        proc = subprocess.Popen([str(exe)], cwd=str(exe.parent))
        info["pcl2_pid"] = proc.pid
        # Wait for a paintable launcher window (the splash draws nothing).
        deadline = time.time() + 90
        while time.time() < deadline:
            wins = sorted(drv.windows_of(proc.pid), key=drv.area_of, reverse=True)
            if wins and _print_window(wins[0], str(out / "_warmup.png")):
                hwnd = wins[0]
                break
            time.sleep(2)
        info["launcher_window"] = drv.title_of(hwnd) if hwnd else None
        if not hwnd:
            (out / "launch.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8", newline="\n")
            return 1
        (out / "_warmup.png").unlink(missing_ok=True)
        time.sleep(SLEEP_BEFORE_FIRST)

    for step in args.step:
        kind, _, value = step.partition(":")
        entry: dict = {"step": step, "at": time.strftime("%H:%M:%S")}
        if kind == "activate":
            entry.update(activate(hwnd))
        elif kind == "click":
            x, y = (int(v) for v in value.split(","))
            entry["activation"] = activate(hwnd)
            entry["sent"] = drv._click(x, y)
            time.sleep(1.2)
        elif kind == "sleep":
            time.sleep(float(value))
        elif kind == "shot":
            shot = out / f"{value}.png"
            entry["saved"] = _print_window(hwnd, str(shot)) if hwnd else False
            if entry["saved"]:
                info["shots"].append(str(shot))
        elif kind == "wait-game":
            limit = float(value or 180)
            deadline = time.time() + limit
            gw = None
            while time.time() < deadline:
                gw = game_window()
                if gw and _print_window(gw, str(out / "game-window.png")):
                    break
                gw = None
                time.sleep(3)
            entry["found"] = bool(gw)
            if gw:
                entry["title"] = drv.title_of(gw)
                info["shots"].append(str(out / "game-window.png"))
        elif kind == "ps":
            entry["java"] = java_command_lines()
        elif kind == "game-activate":
            gw = game_window()
            entry["found"] = bool(gw)
            if gw:
                entry["rect"] = rect_of(gw)
                entry["title"] = drv.title_of(gw)
                entry["activation"] = activate(gw)
        elif kind == "click-game":
            x, y = (int(v) for v in value.split(","))
            gw = game_window()
            if not gw:
                entry["error"] = "no game window"
            else:
                # Activate FIRST: SW_RESTORE puts a minimized/raised window back at its own
                # position, so a rectangle measured before that is stale - the first attempt landed
                # 119 px off and toggled 允许作弊 instead of pressing 创建新的世界.
                entry["activation"] = activate(gw)
                time.sleep(0.6)
                rect = rect_of(gw)
                entry["rect"] = rect
                entry["screen_at"] = [rect[0] + x, rect[1] + y]
                entry["sent"] = drv._click(rect[0] + x, rect[1] + y)
                time.sleep(1.5)
        elif kind == "shot-game":
            gw = game_window()
            shot = out / f"{value}.png"
            entry["saved"] = bool(gw) and _print_window(gw, str(shot))
            if entry["saved"]:
                info["shots"].append(str(shot))
        elif kind == "wait-world":
            limit = float(value or 300)
            deadline = time.time() + limit
            markers: dict = {}
            while time.time() < deadline:
                markers = latest_log_markers(game, info.get("version"))
                blob = " ".join(markers.get("world") or [])
                if "Preparing spawn area" in blob or "Time elapsed:" in blob:
                    break
                if markers.get("crashed"):
                    break
                time.sleep(3)
            entry["markers"] = markers
            time.sleep(3)
            gw = game_window()
            if gw and _print_window(gw, str(out / "in-game.png")):
                info["shots"].append(str(out / "in-game.png"))
                entry["saved"] = True
        elif kind == "wait-title":
            # The splash screen is already a window: "a window exists" is not "the game is up".
            # Wait for the log line the title screen emits, then grab again.
            limit = float(value or 240)
            deadline = time.time() + limit
            reached = False
            while time.time() < deadline:
                marks = latest_log_markers(game, info.get("version"))
                if marks.get("title_screen"):
                    reached = True
                    break
                if marks.get("crashed"):
                    break
                time.sleep(2)
            entry["title_screen"] = reached
            entry["markers"] = latest_log_markers(game, info.get("version"))
            time.sleep(3)
            gw = game_window()
            if gw and _print_window(gw, str(out / "game-title.png")):
                info["shots"].append(str(out / "game-title.png"))
                entry["saved"] = True
        elif kind == "log":
            entry["markers"] = latest_log_markers(game, info.get("version"))
        info["actions"].append(entry)

    info["markers"] = latest_log_markers(game, info.get("version"))
    (out / "drive.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8", newline="\n")
    print(json.dumps({k: info[k] for k in ("launcher_window", "actions") if k in info},
                     ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
