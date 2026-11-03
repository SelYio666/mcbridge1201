"""p235: real OS keyboard inside a world - T opens chat, Esc closes it.

Finding recorded here: synthetic mouse clicks do not engage Minecraft's cursor grab in this
setup (three attempts, cursor never recentred), so the inventory/pause keys - which vanilla
handles in handleKeybinds under the grabbed state - cannot be exercised this way. The chat key
is handled directly in keyPressed, so it works, and that is what this probe asserts.

Every key is gated on GetForegroundWindow() == the game window. Uses a disposable copy of the
p229 test world; never the player's saves.
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
WORLD = "p235-world"
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


def raise_and_check(hwnd) -> bool:
    user32.ShowWindow(hwnd, 9)
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.9)
    return user32.GetForegroundWindow() == hwnd


def shot(hwnd) -> Image.Image:
    l, t, r, b = rect(hwnd)
    return ImageGrab.grab(bbox=(l, t, r, b))


def bottom_diff(a: Image.Image, b: Image.Image) -> float:
    a = a.crop((0, int(a.height * 0.78), a.width, a.height))
    b = b.crop((0, int(b.height * 0.78), b.width, b.height))
    d = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).resize((160, 90))
    px = d.load()
    return sum(sum(px[x, y]) for x in range(160) for y in range(90)) / (160 * 90)


def send_key(vk: int) -> None:
    """SendInput with a scan code (keybd_event(vk, 0, ...) is ignored for letters by GLFW here)."""
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

    cmd, log, _ = mclaunch.build_command(VERSION, GAME, "P235", "2G",
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
        checks["foreground"] = raise_and_check(hwnd)
        if not checks["foreground"]:
            print(json.dumps({"aborted": "not foreground"}))
            return 4

        l, t, r, b = rect(hwnd)
        cx, cy = (l + r) // 2, (t + b) // 2
        user32.SetCursorPos(l + 30, t + 40)
        time.sleep(0.5)
        pos = wt.POINT()
        user32.GetCursorPos(ctypes.byref(pos))
        checks["mouse_grabbed"] = abs(pos.x - cx) < 150 and abs(pos.y - cy) < 150

        base = shot(hwnd)
        base.save(RUN / "in-game.png")

        if user32.GetForegroundWindow() == hwnd:
            send_key(0x54)  # T
        time.sleep(2.0)
        chat = shot(hwnd)
        chat.save(RUN / "chat.png")
        checks["chat_opens"] = bottom_diff(base, chat) > 2.0

        if user32.GetForegroundWindow() == hwnd:
            user32.keybd_event(0x1B, 0, 0, 0)
            time.sleep(0.06)
            user32.keybd_event(0x1B, 0, 2, 0)
        time.sleep(2.0)
        closed = shot(hwnd)
        closed.save(RUN / "chat-closed.png")
        checks["chat_closes"] = bottom_diff(base, closed) < bottom_diff(base, chat)

        required = ("joined", "foreground", "chat_opens", "chat_closes")
        payload = {"checks": checks,
                   "passed": all(bool(checks.get(k)) for k in required),
                   "required": list(required),
                   "diffs": {"chat_bottom": round(bottom_diff(base, chat), 2),
                             "closed_bottom": round(bottom_diff(base, closed), 2)},
                   "note": ("mouse_grabbed is expected to stay false: synthetic clicks do not "
                            "engage the GLFW cursor grab here, so inventory/pause keys (handled "
                            "in handleKeybinds under the grabbed state) are out of scope.")}
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
