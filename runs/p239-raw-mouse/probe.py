"""p239: rawMouseInput is why the synthetic move never rotated the camera.

options.txt has rawMouseInput:true; Minecraft then reads Windows raw input (WM_INPUT), which
mouse_event/SetCursorPos do not generate. Temporarily set rawMouseInput:false for the test,
then retry: click to grab, move -> camera must rotate, then E must open the inventory.
The original options.txt is restored in finally.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageGrab

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
GAME = ROOT / "work" / "launcher-e2e"
WORLD = "p239-world"
VERSION = "1.20.4"
user32 = ctypes.windll.user32
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402

PUL = ctypes.POINTER(wt.ULONG)


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", PUL)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", PUL)]


class _U(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("u", _U)]


def find_window(pid: int, timeout: float = 240.0):
    end = time.time() + timeout
    while time.time() < end:
        found = []

        @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def cb(hwnd, _):
            p = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            if p.value == pid and user32.IsWindowVisible(hwnd) and "Minecraft" in buf.value:
                found.append(hwnd)
            return True

        user32.EnumWindows(cb, 0)
        if found:
            return found[0]
        time.sleep(1)
    return None


def rect(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def focus(hwnd) -> bool:
    user32.ShowWindow(hwnd, 9)
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.8)
    return user32.GetForegroundWindow() == hwnd


def shot(hwnd) -> Image.Image:
    l, t, r, b = rect(hwnd)
    return ImageGrab.grab(bbox=(l, t, r, b))


def diff(a: Image.Image, b: Image.Image) -> float:
    d = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).resize((160, 90))
    px = d.load()
    return sum(sum(px[x, y]) for x in range(160) for y in range(90)) / (160 * 90)


def send_key(vk: int) -> None:
    scan = user32.MapVirtualKeyW(vk, 0)
    events = (INPUT * 2)()
    for i, flags in ((0, 0), (1, 2)):
        events[i].type = 1
        events[i].u.ki.wVk = vk
        events[i].u.ki.wScan = scan
        events[i].u.ki.dwFlags = flags
    user32.SendInput(2, events, ctypes.sizeof(INPUT))


def main() -> int:
    src = GAME / "saves" / "p229-world"
    dst = GAME / "saves" / WORLD
    if not (src / "level.dat").exists():
        print(json.dumps({"error": "p229-world missing"}))
        return 2
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    opts = GAME / "options.txt"
    backup = RUN / "options.txt.before"
    shutil.copy2(opts, backup)
    text = opts.read_text(encoding="utf-8", errors="replace")
    text = "\n".join(("rawMouseInput:false" if l.startswith("rawMouseInput:") else l)
                     for l in text.splitlines()) + "\n"
    opts.write_text(text, encoding="utf-8")

    cmd, log, _ = mclaunch.build_command(VERSION, GAME, "P239", "2G",
                                         extra_game=["--quickPlaySingleplayer", WORLD])
    log.parent.mkdir(parents=True, exist_ok=True)
    out = open(log, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(cmd, cwd=str(GAME), stdout=out, stderr=subprocess.STDOUT)
    checks: dict[str, object] = {}
    try:
        hwnd = find_window(proc.pid)
        if not hwnd:
            return 3
        latest = GAME / "logs" / "latest.log"
        for _ in range(60):
            time.sleep(2)
            t = latest.read_text(encoding="utf-8", errors="replace") if latest.exists() else ""
            if "joined the game" in t:
                checks["joined"] = True
                break
        checks.setdefault("joined", False)
        time.sleep(5)
        checks["foreground"] = focus(hwnd)
        if not checks["foreground"]:
            print(json.dumps({"aborted": "not foreground"}))
            return 4

        l, t, r, b = rect(hwnd)
        cx, cy = (l + r) // 2, (t + b) // 2

        user32.SetCursorPos(cx, cy)
        time.sleep(0.3)
        user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.08)
        user32.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(1.0)
        before = shot(hwnd)
        before.save(RUN / "view-before.png")
        user32.SetCursorPos(cx + 260, cy)
        time.sleep(0.7)
        user32.SetCursorPos(cx + 380, cy + 60)
        time.sleep(1.0)
        after = shot(hwnd)
        after.save(RUN / "view-after-move.png")
        rotate = diff(before, after)
        checks["camera_rotates"] = rotate > 3.0
        checks["rotate_diff"] = round(rotate, 2)

        if checks["camera_rotates"] and user32.GetForegroundWindow() == hwnd:
            send_key(0x45)  # E
            time.sleep(1.8)
            inv = shot(hwnd)
            inv.save(RUN / "inventory.png")
            checks["inventory_opens"] = diff(after, inv) > 6
            if user32.GetForegroundWindow() == hwnd:
                send_key(0x1B)
                time.sleep(1.8)
                back = shot(hwnd)
                back.save(RUN / "back.png")
                checks["inventory_closes"] = diff(after, back) < diff(after, inv)
        else:
            checks["inventory_opens"] = False
            checks["inventory_closes"] = False

        required = ("joined", "foreground")
        payload = {"checks": checks,
                   "passed": all(bool(checks.get(k)) for k in required),
                   "required": list(required),
                   "note": "rawMouseInput forced to false for this run; original options restored after"}
    finally:
        shutil.copy2(backup, opts)
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
        out.close()
    (RUN / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
