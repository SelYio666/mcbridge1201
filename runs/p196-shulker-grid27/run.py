#!/usr/bin/env python3
"""p196: Shulker grid residuals - multi-item grid, FULL preview, real mouse hover.

All client interactions are probe-driven (p191 method: raw Mouse fields + real Keyboard.onKey);
the harness only coordinates the dedicated server and takes screenshots. Because the probe
registers NO HudRenderCallback, every SBT_/GRID marker can only come from the REAL inventory
screen tooltip path (vanilla hoveredSlot -> Screen tooltip -> DrawContext.drawTooltip).

Flow: client box (3 diamonds + 2 emeralds, inv slot 9) hovered in COMPACT -> RIGHT_SHIFT held
(the mod default full-preview key) -> FULL grid over the same box -> the dedicated server
console places a real multi-item box in slot 10 (via /item replace, the syntax the integrated
server rejects but the dedicated console accepts, p187/p188) -> probe releases the key, hovers
the server box.
"""
from __future__ import annotations

import argparse
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
FABRIC_API = ROOT / "work" / "instances" / "fabric-1.21.1-server" / "mods" / "fabric-api.jar"
BALM = ROOT / "work" / "corpus" / "deps" / "balm-fabric-1.21.1-21.0.66.jar"
SHULKER = ROOT / "work" / "client" / "shulker-patched2.jar"
SBT = ROOT / "work" / "client" / "sbtpreview.jar"
PROBE = ROOT / "work" / "tmp" / "p196probe.jar"
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
    shutil.copy2(FABRIC_API, CLIENT_MODS / FABRIC_API.name)
    shutil.copy2(BALM, CLIENT_MODS / BALM.name)
    shutil.copy2(SHULKER, CLIENT_MODS / "shulker-patched2.jar")
    shutil.copy2(SBT, CLIENT_MODS / "sbtpreview.jar")
    shutil.copy2(PROBE, CLIENT_MODS / "p196probe.jar")


import ctypes

def focus_window(pid: int) -> int | None:
    import ctypes.wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    found = []

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
    if not found:
        return None
    hwnd = found[0]
    flags = 0x0001 | 0x0002 | 0x0040
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, flags)
    user32.ShowWindow(hwnd, 9)
    user32.BringWindowToTop(hwnd)
    fg = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg, None)
    my_thread = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(my_thread, fg_thread, True)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(my_thread, fg_thread, False)
    return hwnd


def hold_rshift(down: bool) -> None:
    user32 = ctypes.windll.user32
    user32.keybd_event(0xA1, 0x36, 0 if down else 0x0002, 0)  # VK_RSHIFT


def press_escape() -> None:
    user32 = ctypes.windll.user32
    user32.keybd_event(0x1B, 0x01, 0, 0)
    time.sleep(0.15)
    user32.keybd_event(0x1B, 0x01, 0x0002, 0)
    time.sleep(0.5)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    if not PROBE.exists():
        print(f"missing probe jar: {PROBE}; run build.py first", file=sys.stderr)
        return 2
    setup_mods()
    # The mod's default preview flow requires the preview request; force always-on (p187 lesson).
    config_dir = CLIENT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "shulkerboxtooltip.json5").write_text(
        "{\n  \"preview\": {\n    \"enable\": true,\n    \"alwaysOn\": true,\n    \"previewKey\": \"key.keyboard.f\"\n  }\n}\n",
        encoding="utf-8")

    # Server props: creative/peaceful survival-inventory opened by code (p187 setup).
    props = SERVER / "server.properties"
    backup = RUN / "server.properties.before"
    if props.exists():
        shutil.copy2(props, backup)
    settings = {"server-port": PORT, "difficulty": "peaceful", "gamemode": "creative",
                "force-gamemode": "true", "spawn-monsters": "false"}
    text = props.read_text(encoding="utf-8", errors="replace") if props.exists() else ""
    lines, seen = [], set()
    for line in text.splitlines():
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

    java_home = os.environ.get("JAVA_HOME") or str(ROOT.parent / ".toolchain" / "jdk")
    java = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java")
    server_log = RUN / "server.log"
    server_log.write_text("", encoding="utf-8")
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
                client = subprocess.Popen(cmd, cwd=str(CLIENT), stdout=cout,
                                          stderr=subprocess.STDOUT)
                try:
                    # Phase A+B: client box hover, then FULL. Place the server box only after
                    # the FULL press so the probe's phase order is deterministic.
                    deadline = time.time() + args.timeout
                    full_seen = False
                    survival_seen = False
                    box_placed = False
                    while time.time() < deadline:
                        text = read_text(client_log)
                        if not full_seen and "P196_FULL_REQUEST" in text:
                            full_seen = True
                            # FULL renders for ~6 s (probe holds the poll-synthesized
                            # right shift); screenshot mid-window, then survival.
                            time.sleep(3)
                            _grab_window(str(RUN / "after-full.png"), client.pid)
                            server.stdin.write(
                                (f"gamemode survival {USER}\n").encode("utf-8"))
                            server.stdin.flush()
                            print("switched GridUser to survival")
                        if full_seen and not survival_seen and "P196_SURVIVAL_SCREEN" in text:
                            survival_seen = True
                            server.stdin.write((
                                f"item replace entity {USER} container.10 with"
                                " minecraft:shulker_box[minecraft:container=["
                                '{slot:0,item:{id:"minecraft:diamond",count:2}},'
                                '{slot:1,item:{id:"minecraft:emerald",count:4}}]]'
                                "\n").encode("utf-8"))
                            server.stdin.write(
                                (f"data get entity {USER} Inventory[{{Slot:10b}}]" + "\n").encode())
                            server.stdin.flush()
                            box_placed = True
                            print("server multi-item box placed in slot 10")
                        if box_placed and "P196_SERVER_AIM" in text:
                            break
                        if client.poll() is not None:
                            break
                        time.sleep(1)
                        if "P196_SERVER_AIM" in text:
                            break
                        if client.poll() is not None:
                            break
                        time.sleep(1)
                    if not full_seen:
                        print("FULL request never happened; client tail:")
                        print("\n".join(read_text(client_log).splitlines()[-12:]))
                        return 1
                    time.sleep(5)  # server-box hover frames
                    _grab_window(str(RUN / "after-server.png"), client.pid)
                    time.sleep(1)
                    _grab_window(str(RUN / "after-compact.png"), client.pid)

                    text = read_text(client_log)
                    ser = read_text(server_log)
                    drawitems = [line.split("GRID_DRAWITEMS ", 1)[1]
                                 for line in text.splitlines() if "GRID_DRAWITEMS " in line]
                    drawitem = [line.split("GRID_DRAWITEM ", 1)[1]
                                for line in text.splitlines() if "GRID_DRAWITEM " in line]
                    # split phases: server aim marker position in the log
                    full_idx = text.find("P196_FULL_REQUEST")
                    server_idx = text.find("P196_SERVER_AIM")
                    client_text = text[:full_idx] if full_idx >= 0 else text
                    server_text = text[server_idx:] if server_idx >= 0 else ""
                    client_drawitems = [line.split("GRID_DRAWITEMS ", 1)[1]
                                        for line in client_text.splitlines() if "GRID_DRAWITEMS " in line]
                    server_drawitems = [line.split("GRID_DRAWITEMS ", 1)[1]
                                        for line in server_text.splitlines() if "GRID_DRAWITEMS " in line]
                    server_drawitem = [line.split("GRID_DRAWITEM ", 1)[1]
                                       for line in server_text.splitlines() if "GRID_DRAWITEM " in line]
                    client_items2 = any("items=27" in d
                                        for d in client_drawitems)
                    full_render = any("type=FULL" in d for d in drawitems)
                    server_items2 = any("first=minecraft:emeraldx4" in d for d in server_drawitems)
                    real_hover = any("DRAWTOOLTIP" in line and "data=com.misterpemodder" in line
                                     for line in client_text.splitlines())
                    result = {
                        "client_multi_items2": client_items2,
                        "full_render": full_render,
                        "server_multi_items2": server_items2,
                        "real_hover_path": real_hover,
                        "drawitems_sample": drawitems[:6],
                        "drawitem_sample": drawitem[:6],
                        "client_tail": text.splitlines()[-16:],
                        "server_tail": ser.splitlines()[-10:],
                    }
                    (RUN / "result.json").write_text(
                        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    print(json.dumps({k: result[k] for k in
                                      ("client_multi_items2", "full_render",
                                       "server_multi_items2", "real_hover_path")},
                                     ensure_ascii=False))
                    ok = (client_items2 and full_render and server_items2 and real_hover)
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
            if backup.exists():
                shutil.copy2(backup, props)


if __name__ == "__main__":
    sys.exit(main())
