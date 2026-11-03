"""p243: same synthetic click on 1.21.1 (the p235-p239 finding is from 1.20.4).

Differential test: if a grabbed camera rotates here but not on 1.20.4, the limit is
version-specific rather than environment-wide. Disposable copy of a 1.21.1 test world.
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
SRC_WORLD = GAME / "saves" / "ColdWorldMap"
WORLD = "p243-world"
VERSION = "fabric-loader-0.19.5-1.21.1"
user32 = ctypes.windll.user32
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402


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


def main() -> int:
    dst = GAME / "saves" / WORLD
    if not (SRC_WORLD / "level.dat").exists():
        print(json.dumps({"error": "ColdWorldMap missing"}))
        return 2
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(SRC_WORLD, dst)

    cmd, log, _ = mclaunch.build_command(VERSION, GAME, "P243", "2G",
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
        time.sleep(6)
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
        before.save(RUN / "view-before-1211.png")
        user32.SetCursorPos(cx + 260, cy)
        time.sleep(0.7)
        user32.SetCursorPos(cx + 380, cy + 60)
        time.sleep(1.0)
        after = shot(hwnd)
        after.save(RUN / "view-after-move-1211.png")
        rotate = diff(before, after)
        checks["camera_rotates"] = rotate > 3.0
        checks["rotate_diff"] = round(rotate, 2)

        payload = {"checks": checks, "version": VERSION,
                   "passed": bool(checks.get("joined") and checks.get("foreground")),
                   "note": "differential vs p235-p239 (1.20.4): camera_rotates tells us whether the grab works here"}
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
