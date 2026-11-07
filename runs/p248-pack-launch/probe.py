"""p248: launch the 缆车末日 modpack (1.20.1 Forge 47.4.20) with this repo's launcher.

The overrides payload (12 Forge mods, 408 config files, one 1.7 GB save, two shader packs) is
copied into an isolated game root; assets/libraries/versions are junctioned read-only. The
probe then quickplays the pack's own world and records what the launcher log says.
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

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
BASE = ROOT / "work" / "launcher-e2e"
GAME = ROOT / "work" / "packtest"
PACK = Path(r"D:\浏览器所下载文件\缆车末日整合包\2.拖入minecraft文件夹中替换")
VERSION = "1.20.1-forge-47.4.28"
WORLD = "缆车末日100天地图"
user32 = ctypes.windll.user32
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402


def link(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], check=True,
                   capture_output=True)


def find_window(pid: int, timeout: float = 300.0):
    end = time.time() + timeout
    while time.time() < end:
        found = []

        @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def cb(hwnd, _):
            p = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            if p.value == pid and user32.IsWindowVisible(hwnd):
                found.append(hwnd)
            return True

        user32.EnumWindows(cb, 0)
        if found:
            return found[0]
        time.sleep(1)
    return None


def prepare() -> None:
    GAME.mkdir(parents=True, exist_ok=True)
    for sub in ("assets", "libraries", "versions"):
        link(BASE / sub, GAME / sub)
    for sub in ("mods", "config", "saves", "shaderpacks"):
        src = PACK / sub
        if sub == "mods":
            src = PACK / "overrides" / "mods"
        dst = GAME / sub
        if dst.exists():
            shutil.rmtree(dst)
        if sub == "mods":
            shutil.copytree(src, dst)
        elif sub == "config":
            shutil.copytree(src, dst)
        elif sub == "shaderpacks":
            shutil.copytree(src, dst)
        else:
            print("copying the 1.7 GB save ...", flush=True)
            shutil.copytree(src, dst)
    shutil.copy2(BASE / "options.txt", GAME / "options.txt")
    extra = ROOT / "work" / "packtest-extra"
    if extra.is_dir():
        for jar in extra.glob("*.jar"):
            shutil.copy2(jar, GAME / "mods" / jar.name)
            print("added dependency", jar.name, flush=True)


def main() -> int:
    prepare()
    print("payload ready at", GAME, flush=True)
    cmd, log, _ = mclaunch.build_command(VERSION, GAME, "PackUser", "3G",
                                         extra_game=["--quickPlaySingleplayer", WORLD])
    log.parent.mkdir(parents=True, exist_ok=True)
    latest = GAME / "logs" / "latest.log"
    latest.unlink(missing_ok=True)
    out = open(log, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(cmd, cwd=str(GAME), stdout=out, stderr=subprocess.STDOUT)
    print("client pid", proc.pid, flush=True)
    result: dict[str, object] = {"version": VERSION, "world": WORLD}
    try:
        joined = False
        for _ in range(120):
            time.sleep(3)
            text = latest.read_text(encoding="utf-8", errors="replace") if latest.exists() else ""
            if "joined the game" in text:
                joined = True
                break
            if proc.poll() is not None:
                break
        result["joined"] = joined
        text = latest.read_text(encoding="utf-8", errors="replace") if latest.exists() else ""
        result["log_bytes"] = len(text)
        result["mod_errors"] = [l for l in text.splitlines()
                                if "ERROR" in l and ("mod" in l.lower() or "mixin" in l.lower())][:10]
        result["loaded_line"] = next((l for l in text.splitlines()
                                      if "mod loading" in l.lower() or "Loaded" in l and "mods" in l.lower()), None)
        hwnd = find_window(proc.pid, timeout=10)
        if hwnd:
            r = wt.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            shot = RUN / "in-game.png"
            ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom)).save(shot)
            result["screenshot"] = str(shot)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        out.close()
    (RUN / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("joined") else 1


if __name__ == "__main__":
    raise SystemExit(main())
