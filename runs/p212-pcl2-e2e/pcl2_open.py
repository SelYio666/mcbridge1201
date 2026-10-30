"""Launch PCL2, screenshot its window, and prove the installed version is listed (p212).

The panel wrote `versions/1.20.4` and the `mcbridge-1.20.4` profile into PCL2's game folder; the
last thing 任务 6 needs is that the launcher itself shows it. PCL2 is a WPF app, so the window is
grabbed with PrintWindow (p204's helper) rather than by reading its UI tree - there is no
automation API here, and claiming "PCL2 shows it" from a file listing would be the wrong kind of
evidence.

The launcher is started from this script and closed again at the end; it is not left running.

Usage:
  python runs/p212-pcl2-e2e/pcl2_open.py --exe "<PCL2 exe>" --out runs/p212-pcl2-e2e
  # optional: --click 120,340 --click 200,400   (screen coords, each followed by a screenshot)
"""
from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from test_launcher_e2e import _grab_window, _print_window  # noqa: E402

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


def _screen_size() -> tuple[int, int]:
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def _click(x: int, y: int) -> int:
    user32 = ctypes.windll.user32
    sw, sh = _screen_size()
    move = INPUT()
    move.type = 0
    move.u.mi = MOUSEINPUT(int(round(x * 65535 / max(sw - 1, 1))),
                           int(round(y * 65535 / max(sh - 1, 1))), 0,
                           MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
    down = INPUT()
    down.type = 0
    down.u.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)
    up = INPUT()
    up.type = 0
    up.u.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)
    array = (INPUT * 3)(move, down, up)
    return int(user32.SendInput(3, array, ctypes.sizeof(INPUT)))


def windows_of(pid: int) -> list[int]:
    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):  # noqa: ANN001
        if not user32.IsWindowVisible(hwnd):
            return True
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            found.append(hwnd)
        return True

    user32.EnumWindows(_enum, 0)
    return found


def area_of(hwnd: int) -> int:
    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)


def title_of(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def _processes_of(image_name: str) -> list[int]:
    """PIDs of a running image, by name (tasklist; no psutil dependency)."""
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/FO", "CSV",
                              "/NH"], capture_output=True, text=True, encoding="ascii",
                             errors="ignore", timeout=30).stdout
    except Exception:  # noqa: BLE001
        return []
    pids: list[int] = []
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == image_name.lower():
            try:
                pids.append(int(parts[1]))
            except ValueError:
                pass
    return pids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--wait", type=int, default=60, help="等一个能画出内容的窗口的秒数")
    ap.add_argument("--click", action="append", default=[], help="x,y（屏幕坐标），可重复")
    ap.add_argument("--keep-open", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    exe = Path(args.exe)
    info: dict = {"exe": str(exe), "exe_exists": exe.is_file()}

    # PCL2 is single-instance: with one already running, a new process exits immediately and the
    # script would find no window while the old launcher sits there showing stale state. Kill any
    # instance of this exe first and say so.
    existing = _processes_of(exe.name)
    info["killed_existing"] = []
    for pid in existing:
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=20)
            info["killed_existing"].append(pid)
        except Exception:  # noqa: BLE001
            pass
    if info["killed_existing"]:
        time.sleep(3)

    proc = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    info["pid"] = proc.pid

    # PCL2 opens a "正在打开，请稍候" splash first and swaps in its real window a few seconds later,
    # so "the window exists" is not enough: wait for the largest window of the process to be
    # paintable (PrintWindow succeeds) before believing anything is on screen.
    hwnd = None
    shot = out / "pcl2-window.png"
    titles: list[str] = []
    deadline = time.time() + args.wait
    while time.time() < deadline:
        wins = sorted(windows_of(proc.pid), key=area_of, reverse=True)
        fresh_titles = [title_of(h) for h in wins]
        if fresh_titles and fresh_titles != titles:
            titles = fresh_titles
        if wins and _print_window(wins[0], str(shot)):
            hwnd = wins[0]
            break
        time.sleep(2)
    info["window_titles"] = titles
    info["window_found"] = bool(hwnd)
    info["window_title"] = title_of(hwnd) if hwnd else None
    info["screenshots"] = [str(shot)] if hwnd else []
    if hwnd:
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        info["window_rect"] = [rect.left, rect.top, rect.right, rect.bottom]
        for i, spec in enumerate(args.click, 1):
            x, y = (int(v) for v in spec.split(","))
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            _click(x, y)
            time.sleep(2.5)
            clicked = out / f"pcl2-click-{i}.png"
            if _print_window(hwnd, str(clicked)):
                info["screenshots"].append(str(clicked))
                info["clicks"] = info.get("clicks", []) + [{"at": [x, y], "shot": str(clicked)}]
    if not args.keep_open:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except Exception:  # noqa: BLE001
            proc.kill()
        info["terminated"] = True
    (out / "pcl2-open.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0 if info["window_found"] else 1


if __name__ == "__main__":
    sys.exit(main())
