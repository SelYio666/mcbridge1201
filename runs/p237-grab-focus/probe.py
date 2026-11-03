"""p237: force GLFW focus (AttachThreadInput) so the in-game click can grab the cursor, then
verify the inventory key.

p235 showed T/chat works but synthetic clicks never engaged the cursor grab, so E (inventory,
handled in handleKeybinds under the grabbed state) could not be tested. p213 used
AttachThreadInput to make synthetic clicks land; try the same before clicking.

Disposable copy of the p229 world; every input gated on the game window being foreground.
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
WORLD = "p237-world"
VERSION = "1.20.4"
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
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


def force_focus(hwnd) -> bool:
    """p213's trick: attach input queues so SetForegroundWindow/SetFocus actually stick."""
    user32.ShowWindow(hwnd, 9)
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)
    fg = user32.GetForegroundWindow()
    tid_fg = user32.GetWindowThreadProcessId(fg, None)
    tid_self = kernel32.GetCurrentThreadId()
    attached = bool(user32.AttachThreadInput(tid_self, tid_fg, True))
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(tid_self, tid_fg, False)
    time.sleep(0.8)
    return user32.GetForegroundWindow() == hwnd


def shot(hwnd) -> Image.Image:
    l, t, r, b = rect(hwnd)
    return ImageGrab.grab(bbox=(l, t, r, b))


def diff_score(a: Image.Image, b: Image.Image) -> float:
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

    cmd, log, _ = mclaunch.build_command(VERSION, GAME, "P237", "2G",
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
            text = latest.read_text(encoding="utf-8", errors="replace") if latest.exists() else ""
            if "joined the game" in text:
                checks["joined"] = True
                break
        checks.setdefault("joined", False)
        time.sleep(5)
        checks["foreground"] = force_focus(hwnd)
        if not checks["foreground"]:
            print(json.dumps({"aborted": "not foreground after AttachThreadInput"}))
            return 4

        l, t, r, b = rect(hwnd)
        cx, cy = (l + r) // 2, (t + b) // 2

        def grabbed_now() -> bool:
            user32.SetCursorPos(l + 30, t + 40)
            time.sleep(0.5)
            pos = wt.POINT()
            user32.GetCursorPos(ctypes.byref(pos))
            return abs(pos.x - cx) < 150 and abs(pos.y - cy) < 150

        grabbed = False
        for attempt in range(3):
            if user32.GetForegroundWindow() != hwnd:
                break
            user32.SetCursorPos(cx, cy)
            time.sleep(0.25)
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            time.sleep(0.08)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.9)
            grabbed = grabbed_now()
            if grabbed:
                break
        checks["mouse_grabbed"] = grabbed
        user32.SetCursorPos(cx, cy)
        time.sleep(0.5)

        base = shot(hwnd)
        base.save(RUN / "in-game.png")

        if grabbed and user32.GetForegroundWindow() == hwnd:
            send_key(0x45)  # E
            time.sleep(1.8)
            inv = shot(hwnd)
            inv.save(RUN / "inventory.png")
            checks["inventory_opens"] = diff_score(base, inv) > 6
            if user32.GetForegroundWindow() == hwnd:
                send_key(0x1B)  # Esc closes inventory
                time.sleep(1.8)
                back = shot(hwnd)
                back.save(RUN / "back.png")
                checks["inventory_closes"] = diff_score(base, back) < diff_score(base, inv)
        else:
            checks["inventory_opens"] = False
            checks["inventory_closes"] = False

        required = ("joined", "foreground")
        payload = {"checks": checks,
                   "passed": all(bool(checks.get(k)) for k in required),
                   "required": list(required),
                   "note": ("inventory_opens is only meaningful when mouse_grabbed is true; "
                            "a false grab is recorded as the finding, not hidden.")}
    finally:
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
