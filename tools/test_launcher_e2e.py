#!/usr/bin/env python3
"""End-to-end launcher regression: install (optional) -> launch -> wait for the main menu -> exit.

Example:

    python tools/test_launcher_e2e.py --root work/launcher-e2e --mc 1.21.1
    python tools/test_launcher_e2e.py --root work/launcher-fresh2 --no-install

Exit 0 when the client reached the main menu (log has "Setting user" and "Backend library"),
1 when it did not, 2 on setup errors.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402


def find_installed(root: Path, mc: str) -> str | None:
    for d in sorted((root / "versions").glob(f"fabric-loader-*-{mc}")):
        if (d / f"{d.name}.json").exists():
            return d.name
    return None


def _print_window(hwnd, path: str) -> bool:
    """Capture the window contents with PrintWindow (independent of Z-order).

    OpenGL windows usually render through DWM; PW_RENDERFULLCONTENT returns the last presented
    frame. Returns False when the call or the bitmap is unusable so the caller can fall back.
    """
    try:
        import ctypes
        from ctypes import wintypes

        from PIL import Image
    except ImportError:
        return False
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return False
    hdc = user32.GetWindowDC(hwnd)
    memdc = gdi32.CreateCompatibleDC(hdc)
    bitmap = gdi32.CreateCompatibleBitmap(hdc, width, height)
    old = gdi32.SelectObject(memdc, bitmap)

    class BitmapInfoHeader(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BitmapInfo(ctypes.Structure):
        _fields_ = [("bmiHeader", BitmapInfoHeader), ("bmiColors", wintypes.DWORD * 3)]

    info = BitmapInfo()
    info.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
    info.bmiHeader.biWidth = width
    info.bmiHeader.biHeight = -height
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0  # BI_RGB
    buffer = ctypes.create_string_buffer(width * height * 4)
    try:
        if not user32.PrintWindow(hwnd, memdc, 2):  # PW_RENDERFULLCONTENT
            return False
        if not gdi32.GetDIBits(memdc, bitmap, 0, height, buffer,
                               ctypes.byref(info), 0):
            return False
        img = Image.frombuffer("RGB", (width, height), buffer, "raw", "BGRX", 0, 1)
        colors = img.getcolors(maxcolors=2)
        if colors and len(colors) == 1:
            return False  # all one colour: OpenGL did not render into the DC
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        img.save(path)
        print("screenshot(printwindow) ->", path, img.size)
        return True
    finally:
        gdi32.SelectObject(memdc, old)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memdc)
        user32.ReleaseDC(hwnd, hdc)


def _grab_window(path: str, pid: int | None = None) -> bool:
    """Bring the Minecraft window to the front and save a screenshot (best effort).

    Returns True only when a PNG was written. When the launched Java PID is known, match the
    window by process id instead of title text; a browser or chat window containing "minecraft"
    in unrelated text must not be captured instead of the game (observed in the p178 A/B run).
    """
    try:
        import ctypes
        from ctypes import wintypes

        from PIL import ImageGrab
    except ImportError:
        print("screenshot skipped: Pillow missing")
        return False
    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):  # noqa: ANN001
        if not user32.IsWindowVisible(hwnd):
            return True
        if pid is not None:
            owner = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid:
                found.append(hwnd)
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        title = buf.value.lower()
        if title.startswith("minecraft"):
            found.append(hwnd)
        return True

    user32.EnumWindows(_enum, 0)
    if not found:
        print(f"screenshot skipped: no Minecraft window (pid={pid})")
        return False
    hwnd = found[0]
    if _print_window(hwnd, path):
        return True
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    # The foreground lock can silently reject SetForegroundWindow when another app owns focus;
    # raise the game above other windows for the grab, then restore. Without this a browser can
    # cover the same screen rect even though the PID match found the game window.
    flags = 0x0001 | 0x0002 | 0x0040  # NOSIZE | NOMOVE | SHOWWINDOW
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, flags)  # HWND_TOPMOST
    user32.BringWindowToTop(hwnd)
    time.sleep(1)
    client = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(client))
    origin = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(origin))
    # Client area only: the window border/title bar can show the app behind it through the
    # transparent frame, which polluted an earlier A/B diff.
    bbox = (origin.x, origin.y, origin.x + client.right, origin.y + client.bottom)
    try:
        img = ImageGrab.grab(bbox=bbox)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        img.save(path)
        print("screenshot ->", path, img.size)
        return True
    except Exception as exc:  # noqa: BLE001
        print("screenshot failed:", exc)
        return False
    finally:
        user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, flags)  # HWND_NOTOPMOST


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT / "work" / "launcher-e2e"))
    ap.add_argument("--mc", default="1.21.1")
    ap.add_argument("--version", help="launch this installed version id instead of installing Fabric")
    ap.add_argument("--username", default="E2EUser")
    ap.add_argument("--require", action="append", default=[],
                    help="extra log marker that must appear (repeatable), e.g. 'Sound engine started'")
    ap.add_argument("--screenshot", help="PNG path: grab the game window once the markers matched")
    ap.add_argument("--no-install", action="store_true")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    try:
        if args.version:
            vid = args.version
            if not (root / "versions" / vid / f"{vid}.json").exists():
                print(f"no installed version {vid} under {root}")
                return 2
        elif args.no_install:
            vid = find_installed(root, args.mc)
            if not vid:
                print(f"no fabric version for {args.mc} under {root}; drop --no-install")
                return 2
        else:
            mclaunch.install_vanilla_launcher_profile(args.mc, root)
            vid = mclaunch.install_fabric(args.mc, root)
    except Exception as exc:  # noqa: BLE001
        print("install failed:", exc)
        return 2

    cmd, log, _ = mclaunch.build_command(vid, root, args.username, "2G")
    log.parent.mkdir(parents=True, exist_ok=True)
    print("launching", vid, "->", log)
    with open(log, "w", encoding="utf-8", errors="replace") as out:
        out.write(" ".join(cmd) + "\n")
        out.flush()
        proc = subprocess.Popen(cmd, cwd=str(root), stdout=out, stderr=subprocess.STDOUT)
        deadline = time.time() + args.timeout
        ok = False
        try:
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
                if (f"Setting user: {args.username}" in text and "Backend library" in text
                        and all(marker in text for marker in args.require)):
                    ok = True
                    if args.screenshot:
                        time.sleep(4)  # let the main menu finish drawing
                        _grab_window(args.screenshot, proc.pid)
                    break
                time.sleep(1)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    for bad in ("AccessDenied", "Uncaught exception in thread"):
        if bad in text:
            print("failed marker:", bad)
            ok = False
    print("RESULT:", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
