#!/usr/bin/env python3
"""p186: client-side container item -> ShulkerBoxTooltip grid render.

Starts the Fabric-API-only dedicated server, installs the converted ShulkerBoxTooltip + companion +
gridprobe on the client, creates a client-side shulker box with a ContainerComponent, opens the
inventory, hovers the slot and screenshots the tooltip.
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
PROBE = ROOT / "work" / "tmp" / "gridprobe.jar"
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
            found.append(hwnd)
        return True

    user32.EnumWindows(_enum, 0)
    return found[0] if found else None


def focus_window(hwnd: int) -> None:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
    user32.ShowWindow(hwnd, 9)
    user32.BringWindowToTop(hwnd)
    fg = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg, None)
    my_thread = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(my_thread, fg_thread, True)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(my_thread, fg_thread, False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    if not PROBE.exists():
        print(f"missing probe jar: {PROBE}; run build.py first", file=sys.stderr)
        return 2
    setup_mods()
    # A previous creeper death persisted GridUser at health 0; wipe that player so the fresh
    # creative/peaceful join does not sit on the death screen forever.
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
                                  cwd=str(SERVER), stdout=out, stderr=subprocess.STDOUT)
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
                    screen = None
                    slot = None
                    while time.time() < deadline:
                        text = read_text(client_log)
                        for line in text.splitlines():
                            if "GRID_SCREEN " in line:
                                fields = {}
                                for part in line.split("GRID_SCREEN ", 1)[1].split():
                                    if "=" in part:
                                        k, v = part.split("=", 1)
                                        fields[k] = v
                                screen = fields
                            elif "GRID_SLOT " in line:
                                fields = {}
                                for part in line.split("GRID_SLOT ", 1)[1].split():
                                    if "=" in part:
                                        k, v = part.split("=", 1)
                                        fields[k] = v
                                slot = fields
                        if screen and slot:
                            break
                        if client.poll() is not None:
                            break
                        time.sleep(1)
                    if not (screen and slot):
                        print("no GRID_SCREEN/GRID_SLOT; client tail:")
                        print("\n".join(read_text(client_log).splitlines()[-16:]))
                        return 1
                    print("screen:", screen, "slot:", slot)
                    hwnd = find_window(client.pid)
                    if not hwnd:
                        print("no client window for pid", client.pid, file=sys.stderr)
                        return 1
                    scale = float(screen.get("scale", "3"))
                    gui_x = float(screen["left"]) + float(slot["x"]) + 8
                    gui_y = float(screen["top"]) + float(slot["y"]) + 8
                    user32 = ctypes.windll.user32
                    focus_window(hwnd)
                    time.sleep(0.8)
                    origin = ctypes.wintypes.POINT(0, 0)
                    user32.ClientToScreen(hwnd, ctypes.byref(origin))
                    px = origin.x + int(gui_x * scale)
                    py = origin.y + int(gui_y * scale)
                    print(f"hovering grid slot gui=({gui_x:.1f},{gui_y:.1f}) physical=({px},{py})")
                    user32.SetCursorPos(px, py)
                    time.sleep(3)
                    _grab_window(str(RUN / "grid.png"), client.pid)
                    text = read_text(client_log)
                    ser = read_text(server_log)
                    wrap_line = next((line for line in text.splitlines() if "SBT_WRAP " in line), "")
                    iter_line = next((line for line in text.splitlines() if "SBT_ITER " in line), "")
                    sbt_seen = ("show=true" in wrap_line and "nonAir=1" in wrap_line)
                    container = ("head=minecraft:diamondx5" in iter_line)
                    result = {
                        "screen": screen,
                        "slot": slot,
                        "physical": [px, py],
                        "sbt_seen": sbt_seen,
                        "container": container,
                        "wrap_line": wrap_line,
                        "iter_line": iter_line,
                        "client_tail": text.splitlines()[-24:],
                        "server_tail": ser.splitlines()[-12:],
                    }
                    (RUN / "result.json").write_text(
                        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    print(json.dumps({k: result[k] for k in ("sbt_seen", "container")},
                                     ensure_ascii=False))
                    print("SBT_WRAP:", wrap_line)
                    print("SBT_ITER:", iter_line)
                    return 0 if (sbt_seen and container) else 1
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
