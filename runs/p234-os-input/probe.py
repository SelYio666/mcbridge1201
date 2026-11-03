"""p234: real OS-level input on the title screen - hover highlight, click, Esc back.

Safety: every input is gated on GetForegroundWindow() == the game window; the script aborts
instead of clicking if the window is not in front. Actions are menu-only (no world writes).
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
BASE = ROOT / "work" / "launcher-e2e"
GD = ROOT / "work" / "tmp" / "p234-gamedir"
VERSION = "fabric-loader-0.19.5-1.21.1"
user32 = ctypes.windll.user32
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402


def link(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        return
    subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], check=True,
                   capture_output=True)


def prepare() -> Path:
    if GD.exists():
        shutil.rmtree(GD)
    GD.mkdir(parents=True)
    for sub in ("assets", "libraries", "versions", ".fabric"):
        link(BASE / sub, GD / sub)
    for sub in ("mods", "saves", "logs", "config", "resourcepacks"):
        (GD / sub).mkdir()
    lines = [l for l in (BASE / "options.txt").read_text(encoding="utf-8", errors="replace").splitlines()
             if not l.startswith(("onboardAccessibility:", "fullscreen:"))]
    lines += ["onboardAccessibility:false", "fullscreen:false"]
    (GD / "options.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return GD


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


def gray_boxes(img: Image.Image):
    px = img.load()
    w, h = img.size
    rows = [y for y in range(h) if sum(1 for x in range(0, w, 4)
            if px[x, y][0] > 95 and abs(px[x, y][0] - px[x, y][1]) < 6
            and abs(px[x, y][1] - px[x, y][2]) < 6) > 40]
    clusters = []
    for y in rows:
        if clusters and y - clusters[-1][-1] <= 4:
            clusters[-1].append(y)
        else:
            clusters.append([y])
    boxes = []
    for c in [c for c in clusters if len(c) >= 8]:
        y0, y1 = c[0], c[-1]
        cols = [x for x in range(w) if any(
            px[x, y][0] > 95 and abs(px[x, y][0] - px[x, y][1]) < 6
            and abs(px[x, y][1] - px[x, y][2]) < 6 for y in range(y0, y1 + 1))]
        gc = []
        for x in cols:
            if gc and x - gc[-1][-1] <= 20:
                gc[-1].append(x)
            else:
                gc.append([x])
        for cc in [cc for cc in gc if 380 <= cc[-1] - cc[0] <= 520]:
            boxes.append((cc[0], y0, cc[-1], y1))
    return boxes


def mean_rgb(img: Image.Image, box) -> float:
    crop = img.crop(box).convert("L")
    data = list(crop.getdata())
    return sum(data) / max(1, len(data))


def diff_score(a: Image.Image, b: Image.Image) -> float:
    d = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    px = d.resize((160, 90)).load()
    return sum(sum(px[x, y]) for x in range(160) for y in range(90)) / (160 * 90)


def click_at(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.15)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.08)
    user32.mouse_event(0x0004, 0, 0, 0, 0)


def main() -> int:
    gd = prepare()
    cmd, log, _ = mclaunch.build_command(VERSION, gd, "P234", "2G")
    log.parent.mkdir(parents=True, exist_ok=True)
    out = open(log, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(cmd, cwd=str(gd), stdout=out, stderr=subprocess.STDOUT)
    checks = {}
    saved_cursor = wt.POINT()
    user32.GetCursorPos(ctypes.byref(saved_cursor))
    try:
        hwnd = find_window(proc.pid)
        if not hwnd:
            return 2
        time.sleep(14)
        checks["foreground"] = raise_and_check(hwnd)
        if not checks["foreground"]:
            print(json.dumps({"aborted": "window not foreground; no input sent"}))
            return 3
        l, t, r, b = rect(hwnd)
        base = shot(hwnd)
        base.save(RUN / "title-before.png")
        boxes = gray_boxes(base)
        if not boxes:
            return 4
        btn = min(boxes, key=lambda x: x[1])  # topmost button = 单人游戏
        cx, cy = (btn[0] + btn[2]) // 2, (btn[1] + btn[3]) // 2
        before = mean_rgb(base, btn)

        user32.SetCursorPos(l + cx, t + cy)
        time.sleep(0.7)
        if user32.GetForegroundWindow() != hwnd:
            print(json.dumps({"aborted": "lost foreground before hover"}))
            return 3
        hover = shot(hwnd)
        hover.save(RUN / "title-hover.png")
        after = mean_rgb(hover, btn)
        checks["hover_brightens"] = after > before + 4
        checks["hover_values"] = [round(before, 1), round(after, 1)]

        if user32.GetForegroundWindow() != hwnd:
            return 3
        click_at(l + cx, t + cy)
        time.sleep(3)
        clicked = shot(hwnd)
        clicked.save(RUN / "after-click.png")
        checks["click_changes_screen"] = diff_score(base, clicked) > 12

        if user32.GetForegroundWindow() == hwnd:
            user32.keybd_event(0x1B, 0, 0, 0)
            user32.keybd_event(0x1B, 0, 2, 0)
            time.sleep(2)
            back = shot(hwnd)
            back.save(RUN / "after-esc.png")
            checks["esc_returns"] = diff_score(base, back) < diff_score(base, clicked)
        else:
            checks["esc_returns"] = False

        checks = {k: v for k, v in checks.items() if k != "hover_values"}
        payload = {"checks": checks, "passed": all(bool(v) for v in checks.values()),
                   "total": len(checks), "hover_values": [round(before, 1), round(after, 1)]}
    finally:
        user32.SetCursorPos(saved_cursor.x, saved_cursor.y)
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
