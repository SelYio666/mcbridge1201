"""p233: two clients, two independent resource packs (red / green panorama), shared assets.

Closes a p231 boundary: the four clients shared assets by junction, so per-client resource
packs were never exercised. Here each game dir gets its own resourcepacks/ + options.txt and
the oracle is the title-screen background colour captured from each game window.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import io
import json
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from PIL import Image, ImageGrab

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
BASE = ROOT / "work" / "launcher-e2e"
VERSION = "fabric-loader-0.19.5-1.21.1"
WORK = ROOT / "work" / "tmp"
user32 = ctypes.windll.user32
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402


def link(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        return
    subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], check=True,
                   capture_output=True)


def make_pack(path: Path, rgb: tuple[int, int, int], label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), rgb).save(buf, "PNG")
    png = buf.getvalue()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", json.dumps({
            "pack": {"pack_format": 34, "description": f"p233 {label}"}
        }))
        for i in range(6):
            z.writestr(f"assets/minecraft/textures/gui/title/background/panorama_{i}.png", png)


def prepare(name: str, rgb, label: str) -> Path:
    gd = WORK / f"p233-gamedir-{name}"
    if gd.exists():
        shutil.rmtree(gd)
    gd.mkdir(parents=True)
    for sub in ("assets", "libraries", "versions", ".fabric"):
        link(BASE / sub, gd / sub)
    for sub in ("mods", "saves", "logs", "config", "resourcepacks"):
        (gd / sub).mkdir()
    opts = (BASE / "options.txt").read_text(encoding="utf-8", errors="replace")
    lines = []
    for line in opts.splitlines():
        if line.startswith(("resourcePacks:", "incompatibleResourcePacks:",
                            "onboardAccessibility:", "fullscreen:")):
            continue
        lines.append(line)
    lines += ['resourcePacks:["vanilla","file/p233-%s.zip"]' % name,
              "incompatibleResourcePacks:[]", "onboardAccessibility:false", "fullscreen:false"]
    (gd / "options.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    make_pack(gd / "resourcepacks" / f"p233-{name}.zip", rgb, label)
    return gd


def window_for_pid(pid: int, timeout: float = 180.0):
    end = time.time() + timeout
    while time.time() < end:
        found = []

        @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def cb(hwnd, _):
            p = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            if p.value == pid and user32.IsWindowVisible(hwnd):
                found.append(hwnd)
            return True

        user32.EnumWindows(cb, 0)
        if found:
            return found[0]
        time.sleep(1)
    return None


def capture(hwnd) -> Image.Image:
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))


def centre_mean(img: Image.Image) -> tuple[int, int, int]:
    w, h = img.size
    box = img.crop((int(w * 0.30), int(h * 0.55), int(w * 0.70), int(h * 0.90))).convert("RGB")
    px = list(box.getdata())
    n = len(px)
    return tuple(sum(c[i] for c in px) // n for i in range(3))


def run_client(name: str, gd: Path, username: str):
    cmd, log, _ = mclaunch.build_command(VERSION, gd, username, "2G")
    log.parent.mkdir(parents=True, exist_ok=True)
    out = open(log, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(cmd, cwd=str(gd), stdout=out, stderr=subprocess.STDOUT)
    hwnd = window_for_pid(proc.pid, 240)
    if not hwnd:
        proc.terminate()
        out.close()
        raise RuntimeError(f"{name}: no window")
    time.sleep(18)  # panorama + pack load settle
    img = capture(hwnd)
    img.save(RUN / f"title-{name}.png")
    mean = centre_mean(img)
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    out.close()
    return mean


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    gd_r = prepare("red", (200, 20, 20), "red")
    gd_g = prepare("green", (20, 200, 20), "green")
    res = {}
    res["red"] = run_client("red", gd_r, "P233Red")
    res["green"] = run_client("green", gd_g, "P233Green")
    checks = {
        "red_is_red": res["red"][0] > res["red"][1] + 40 and res["red"][0] > res["red"][2] + 40,
        "green_is_green": res["green"][1] > res["green"][0] + 40 and res["green"][1] > res["green"][2] + 40,
        "clients_differ": sum(abs(a - b) for a, b in zip(res["red"], res["green"])) >= 100,
        "distinct_game_dirs": gd_r != gd_g,
        "packs_on_disk": (gd_r / "resourcepacks" / "p233-red.zip").is_file()
                          and (gd_g / "resourcepacks" / "p233-green.zip").is_file(),
    }
    payload = {"means": {k: list(v) for k, v in res.items()}, "checks": checks,
               "passed": all(checks.values()), "total": len(checks),
               "note": "assets/libraries shared by junction; only resourcepacks + options are per-client"}
    (RUN / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
