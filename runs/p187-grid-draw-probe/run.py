#!/usr/bin/env python3
"""p187: trace the converted mod's grid draw pipeline while the tooltip is hovered.

Same harness as p186 (client-side ContainerComponent shulker in the creative inventory, hover,
screenshot) plus a probe mixin on BasePreviewRenderer that logs setPreview/drawItems/drawItem.
Diagnostic run: it reports where the diamond disappears instead of gating a feature.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
SERVER = ROOT / "work" / "instances" / "fabric-1.21.1-server-trashslot"
CLIENT = ROOT / "work" / "launcher-e2e"
SERVER_MODS = SERVER / "mods"
CLIENT_MODS = CLIENT / "mods"
FABRIC_API = SERVER_MODS / "fabric-api-0.102.0+1.21.1.jar"
BALM = ROOT / "work" / "corpus" / "deps" / "balm-fabric-1.21.1-21.0.66.jar"
SHULKER = ROOT / "work" / "client" / "shulker-patched2.jar"
SBT = ROOT / "work" / "client" / "sbtpreview.jar"
TRASH = ROOT / "work" / "client" / "trashslot-client-empty.jar"
PROBE = ROOT / "work" / "tmp" / "gridprobe187.jar"
PORT = "25566"
USER = "GridUser"

sys.path.insert(0, str(ROOT / "launcher"))
sys.path.insert(0, str(ROOT / "tools"))
import mclaunch  # noqa: E402
from test_launcher_e2e import _grab_window  # noqa: E402


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def setup_mods() -> None:
    for path in CLIENT_MODS.glob("*.jar"):
        path.unlink()
    shutil.copy2(FABRIC_API, CLIENT_MODS / "fabric-api.jar")
    shutil.copy2(BALM, CLIENT_MODS / BALM.name)
    shutil.copy2(SHULKER, CLIENT_MODS / "shulker-patched2.jar")
    shutil.copy2(SBT, CLIENT_MODS / "sbtpreview.jar")
    shutil.copy2(TRASH, CLIENT_MODS / "trashslot-client-empty.jar")
    shutil.copy2(PROBE, CLIENT_MODS / "gridprobe.jar")
    for path in SERVER_MODS.glob("trashslot*.jar"):
        path.unlink()
    shutil.copy2(TRASH, SERVER_MODS / "trashslot-15.1.5+1.21.1.jar")
    # The mod's default preview flow requires holding the preview keybind; without a config file
    # alwaysOn defaults to false and the renderer early-returns (p187: setPreview ran with the
    # diamond but PreviewType.NO_PREVIEW skipped drawItems). Force the preview always on.
    config_dir = CLIENT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "shulkerboxtooltip.json5").write_text(
        "{\n"
        '  "preview": {\n'
        '    "enable": true,\n'
        '    "alwaysOn": true\n'
        "  }\n"
        "}\n",
        encoding="utf-8")


def find_window(pid: int) -> int | None:
    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _enum(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            rect = ctypes.wintypes.RECT()
            if user32.GetClientRect(hwnd, ctypes.byref(rect)):
                w, h = rect.right - rect.left, rect.bottom - rect.top
                if w >= 800 and h >= 600:
                    found.append(hwnd)
        return True

    user32.EnumWindows(_enum, 0)
    # Prefer the real game client (1280x720 content) over small helper windows.
    found.sort(key=lambda hwnd: -_client_area(hwnd))
    return found[0] if found else None


def _client_area(hwnd: int) -> int:
    rect = ctypes.wintypes.RECT()
    if not ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return 0
    return (rect.right - rect.left) * (rect.bottom - rect.top)


def focus_window(hwnd: int) -> None:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    flags = 0x0001 | 0x0002 | 0x0040
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, flags)  # HWND_TOPMOST, keep size/position
    user32.ShowWindow(hwnd, 9)
    user32.BringWindowToTop(hwnd)
    fg = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg, None)
    my_thread = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(my_thread, fg_thread, True)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(my_thread, fg_thread, False)


def locate_shulker(image_path: Path) -> tuple[int, int] | None:
    """Find the hotbar shulker box in a window screenshot by its purple (r==b, low g) pixels."""
    try:
        from PIL import Image
    except ImportError:
        return None
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    x0, x1 = int(w * 0.30), int(w * 0.46)
    y0, y1 = int(h * 0.58), int(h * 0.74)
    sx = sy = count = 0
    px = img.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = px[x, y]
            if abs(r - b) < 14 and r - g > 18 and r > 40:
                sx += x
                sy += y
                count += 1
    if count < 25:
        return None
    return (sx // count, sy // count)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    if not PROBE.exists():
        print(f"missing probe jar: {PROBE}; run build.py first", file=sys.stderr)
        return 2
    setup_mods()
    try:
        users = json.loads(read_text(SERVER / "usercache.json") or "[]")
    except ValueError:
        users = []
    for entry in users:
        if entry.get("name") != USER:
            continue
        uid = entry.get("uuid")
        for sub, ext in (("playerdata", ".dat"), ("stats", ".json"), ("advancements", ".json")):
            path = SERVER / "world" / sub / f"{uid}{ext}"
            if path.exists():
                path.unlink()
                print("removed", path)
    props = SERVER / "server.properties"
    backup = None
    if props.exists():
        backup = props.read_text(encoding="utf-8", errors="replace")
        settings = {
            "server-port": PORT,
            "difficulty": "peaceful",
            "gamemode": "creative",
            "force-gamemode": "true",
            "spawn-monsters": "false",
        }
        lines = []
        seen = set()
        for line in backup.splitlines():
            key = line.split("=", 1)[0] if "=" in line else ""
            if key in settings:
                lines.append(f"{key}={settings[key]}")
                seen.add(key)
            else:
                lines.append(line)
        for key, value in settings.items():
            if key not in seen:
                lines.append(f"{key}={value}")
        props.write_text("\n".join(lines) + "\n", encoding="utf-8")

    java_home = os.environ.get("JAVA_HOME") or str(ROOT.parent / ".toolchain" / "jdk")
    java = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java")
    server_log = RUN / "server.log"
    with server_log.open("w", encoding="utf-8", errors="replace") as out:
        server = subprocess.Popen([str(java), "-Xmx2G", "-jar", "fabric-server-launch.jar", "nogui"],
                                  cwd=str(SERVER), stdout=out, stderr=subprocess.STDOUT,
                                  stdin=subprocess.PIPE)
        try:
            deadline = time.time() + 120
            while time.time() < deadline:
                if server.poll() is not None:
                    break
                if "Done (" in read_text(server_log):
                    break
                time.sleep(1)
            if "Done (" not in read_text(server_log):
                print("server did not start; tail:")
                print("\n".join(read_text(server_log).splitlines()[-12:]))
                return 2
            print("server ready")
            client_log = RUN / "client.log"
            client_log.write_text("", encoding="utf-8")
            cmd, _, _ = mclaunch.build_command(
                "fabric-loader-0.19.5-1.21.1", CLIENT, USER, "2G",
                extra_game=["--quickPlayMultiplayer", f"127.0.0.1:{PORT}",
                            "--width", "1280", "--height", "720"])
            with client_log.open("w", encoding="utf-8", errors="replace") as cout:
                cout.write(" ".join(cmd) + "\n")
                cout.flush()
                client = subprocess.Popen(cmd, cwd=str(CLIENT), stdout=cout, stderr=subprocess.STDOUT)
                try:
                    deadline = time.time() + args.timeout
                    hud_seen = False
                    server_item_sent = False
                    server_item_seen = False
                    while time.time() < deadline:
                        text = read_text(client_log)
                        hud_seen = "GRID_HUD_START" in text
                        server_item_seen = "GRID_SERVERBOX" in text
                        if hud_seen and not server_item_sent and "GRID_INV_OPEN" in text:
                            # Give the player a REAL server-side shulker box so the synced stack
                            # (not just the client-side probe item) exercises the preview path.
                            server_item_sent = True
                            server.stdin.write((
                                "item replace entity GridUser container.3 with"
                                " minecraft:shulker_box[minecraft:container=["
                                '{slot:0,item:{id:"minecraft:diamond",count:5}}]]\n').encode("utf-8"))
                            server.stdin.flush()
                            print("sent /item replace for the server-side box")
                        if hud_seen and "GRID_DRAWITEMS " in text and (
                                not server_item_sent or server_item_seen):
                            break
                        if client.poll() is not None:
                            break
                        time.sleep(1)
                    if not hud_seen:
                        print("no GRID_HUD_START; client tail:")
                        print("\n".join(read_text(client_log).splitlines()[-16:]))
                        return 1
                    if server_item_sent and not server_item_seen:
                        print("server-side box never synced; continuing with the client-side item")
                    time.sleep(2.5)
                    _grab_window(str(RUN / "grid.png"), client.pid)
                    text = read_text(client_log)
                    ser = read_text(server_log)

                    def first_line(marker: str) -> str:
                        return next((line for line in text.splitlines() if marker in line), "")

                    hud_line = first_line("GRID_HUD frame=")
                    hud_start = first_line("GRID_HUD_START ")
                    serverbox_line = first_line("GRID_SERVERBOX ")
                    moddata_line = first_line("MODDATA return ")
                    setrender_line = first_line("GRID_SETRENDER ")
                    drawitems_line = first_line("GRID_DRAWITEMS ")
                    drawitem_line = first_line("GRID_DRAWITEM ")
                    result = {
                        "hud_start": hud_start,
                        "hud_line": hud_line,
                        "serverbox_line": serverbox_line,
                        "moddata_line": moddata_line,
                        "setrender_line": setrender_line,
                        "drawitems_line": drawitems_line,
                        "drawitem_line": drawitem_line,
                        "grid_markers": {
                            "hud_frames": text.count("GRID_HUD frame="),
                            "serverbox": text.count("GRID_SERVERBOX "),
                            "moddata_returns": text.count("MODDATA return "),
                            "setrender": text.count("GRID_SETRENDER "),
                            "drawitems": text.count("GRID_DRAWITEMS "),
                            "drawitem": text.count("GRID_DRAWITEM "),
                        },
                        "client_tail": text.splitlines()[-24:],
                        "server_tail": ser.splitlines()[-12:],
                    }
                    (RUN / "result.json").write_text(
                        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    print(json.dumps({k: result[k] for k in
                                      ("hud_line", "serverbox_line", "setrender_line",
                                       "drawitems_line", "drawitem_line", "grid_markers")},
                                     ensure_ascii=False))
                    # Gate: the real tooltip pipeline reached the mod's renderer with items, and
                    # the server-synced shulker is the tooltip source when one was placed.
                    ok = bool(drawitems_line) and bool(drawitem_line) and (
                        not server_item_sent or server_item_seen)
                    return 0 if ok else 1
                finally:
                    if client.poll() is None:
                        client.terminate()
                        try:
                            client.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            client.kill()
        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill()
            if backup is not None:
                props.write_text(backup, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
