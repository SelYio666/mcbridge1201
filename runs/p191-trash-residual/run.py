#!/usr/bin/env python3
"""p191 residual scene A: creative inventory tab (27 main slots) + creative list slots.

Dedicated creative server (like p189). The client opens the creative screen; the p191 probe
switches to the INVENTORY tab at tick 65 (the only tab with Type.INVENTORY, selected through the
CreativeTabInvoker test mixin) and dumps the menu slots every second. The server console places
5 diamonds on hotbar 0 (control) and 7 diamonds on main-inventory slot 18 (container.18).

Flow: hover the main-inventory slot 18 on the inventory tab -> Delete -> the companion's
generalized mapping must reach the server as InventoryMenu slot 18 (SERVER_DELETE slot=18) and
inv18 must become empty. At tick 200 the probe switches back to the default tab; the harness then
hovers a creative-list slot (class_482, container=CreativeInventory) and presses Delete -> NO
server delete may happen (upstream semantics: only player-inventory slots are deletable from the
creative screen; the companion's container check excludes the virtual list slots).
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
FABRIC_API = ROOT / "work" / "instances" / "fabric-1.21.1-server" / "mods" / "fabric-api.jar"
BALM = SERVER_MODS / "balm-fabric-1.21.1.jar"
TRASH_JAR = ROOT / "work" / "client" / "trashslot-client-empty.jar"
PROBE = ROOT / "work" / "tmp" / "trashresidual.jar"
COMPANION = ROOT / "work" / "client" / "trashcreative-fix.jar"
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
    backup = ROOT / "work" / "tmp" / "p191-mod-backup"
    backup.mkdir(parents=True, exist_ok=True)
    for path in SERVER_MODS.glob("*.jar"):
        shutil.copy2(path, backup / path.name)
    for path in CLIENT_MODS.glob("*.jar"):
        shutil.copy2(path, backup / f"client-{path.name}")
    for path in CLIENT_MODS.glob("*.jar"):
        path.unlink()
    shutil.copy2(FABRIC_API, CLIENT_MODS / FABRIC_API.name)
    shutil.copy2(BALM, CLIENT_MODS / BALM.name)
    shutil.copy2(TRASH_JAR, CLIENT_MODS / "trashslot-client-empty.jar")
    shutil.copy2(PROBE, CLIENT_MODS / "trashresidual.jar")
    shutil.copy2(COMPANION, CLIENT_MODS / "trashcreative-fix.jar")
    for name in ("trashslot-15.1.5+1.21.1.jar", "trashslot-client-empty.jar"):
        (SERVER_MODS / name).unlink(missing_ok=True)
    shutil.copy2(TRASH_JAR, SERVER_MODS / "trashslot-15.1.5+1.21.1.jar")
    for src in (FABRIC_API, BALM):
        dst = SERVER_MODS / src.name
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
    shutil.copy2(PROBE, SERVER_MODS / "trashresidual.jar")


def set_server_config() -> None:
    props = SERVER / "server.properties"
    if props.exists():
        shutil.copy2(props, RUN / "server.properties.before")
    settings = {
        "server-port": PORT,
        "difficulty": "peaceful",
        "gamemode": "creative",
        "force-gamemode": "true",
        "spawn-monsters": "false",
    }
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


def focus_and_click(hwnd: int, x: int, y: int) -> None:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
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
    user32.SetCursorPos(x, y)
    time.sleep(0.6)


def focus_window_only(hwnd: int) -> bool:
    """Keyboard-focus the window without touching the cursor (the probe aims the in-game mouse)."""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    for _ in range(4):
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
        if user32.GetForegroundWindow() == hwnd:
            return True
        time.sleep(0.8)
    return False


def press_delete() -> None:
    user32 = ctypes.windll.user32
    extended = 0x0001
    keyup = 0x0002
    user32.keybd_event(0x2E, 0x53, extended, 0)
    time.sleep(0.15)
    user32.keybd_event(0x2E, 0x53, extended | keyup, 0)
    time.sleep(0.5)


def parse_fields(line: str, marker: str) -> dict:
    fields = {}
    for part in line.split(marker, 1)[1].split():
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k] = v
    return fields


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    if not PROBE.exists():
        print(f"missing probe jar: {PROBE}; run build.py first", file=sys.stderr)
        return 2
    setup_mods()
    set_server_config()

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
                    deadline = time.time() + args.timeout
                    while time.time() < deadline:
                        if "RES_OPEN" in read_text(client_log):
                            server.stdin.write((f"item replace entity {USER} container.0"
                                                " with minecraft:diamond 5\n").encode("utf-8"))
                            server.stdin.write((f"item replace entity {USER} container.18"
                                                " with minecraft:diamond 7\n").encode("utf-8"))
                            server.stdin.flush()
                            print("placed 5 diamonds on hotbar 0 and 7 on main slot 18")
                            break
                        if client.poll() is not None:
                            break
                        time.sleep(1)
                    # Items placed; the probe drives the whole interaction (aim + Delete).
                    print("waiting for the probe's inv-phase Delete")
                    hwnd = find_window(client.pid)
                    if not hwnd:
                        print("no client window", file=sys.stderr)
                        return 1
                    geom = parse_fields(next(line for line in read_text(client_log).splitlines()
                                             if "RES_GEOM" in line), "RES_GEOM")
                    user32 = ctypes.windll.user32
                    origin = ctypes.wintypes.POINT(0, 0)
                    user32.ClientToScreen(hwnd, ctypes.byref(origin))
                    scale = float(geom.get("scale", "2"))

                    def latest_game_mouse() -> tuple[float, float] | None:
                        """The newest RES_MOUSE line = where the GAME thinks the cursor is (gui)."""
                        last = None
                        for line in read_text(client_log).splitlines():
                            if "RES_MOUSE" in line:
                                last = line
                        if not last:
                            return None
                        vals = {}
                        for part in last.split("RES_MOUSE ", 1)[1].split():
                            if "=" in part:
                                k, v = part.split("=", 1)
                                vals[k] = v
                        return float(vals["gx"]), float(vals["gy"])

                    def hover(line_fields: dict) -> tuple[int, int]:
                        # Feedback aiming: place the cursor, read the game's own mouse report,
                        # correct by the delta. Immune to window-origin drift after focus().
                        gx = float(geom["left"]) + float(line_fields["x"]) + 8
                        gy = float(geom["top"]) + float(line_fields["y"]) + 8
                        px = origin.x + int(gx * scale)
                        py = origin.y + int(gy * scale)
                        for _ in range(4):
                            focus_and_click(hwnd, px, py)
                            if user32.GetForegroundWindow() == hwnd:
                                break
                            time.sleep(0.8)
                        time.sleep(1.2)  # let a fresh RES_MOUSE line arrive
                        for _ in range(6):
                            game = latest_game_mouse()
                            if game:
                                dx = gx - game[0]
                                dy = gy - game[1]
                                if abs(dx) < 3 and abs(dy) < 3:
                                    break
                                px += int(dx * scale)
                                py += int(dy * scale)
                                user32.SetCursorPos(px, py)
                                time.sleep(1.2)
                        return px, py

                    # Phase 2: wait for the probe's inventory-tab aiming, then Delete.
                    deadline_aim = time.time() + 90
                    while time.time() < deadline_aim:
                        if any("RES_AIM phase=inv" in line
                               for line in read_text(client_log).splitlines()):
                            break
                        if client.poll() is not None:
                            break
                        time.sleep(1)
                    deadline_key = time.time() + 120
                    while time.time() < deadline_key:
                        if any("RES_KEY phase=inv" in line
                               for line in read_text(client_log).splitlines()):
                            break
                        if client.poll() is not None:
                            break
                        time.sleep(1)
                    time.sleep(4)  # both scheduled inv presses + server settle
                    _grab_window(str(RUN / "after-inv-delete.png"), client.pid)
                    deletes_before2 = read_text(server_log).count("SERVER_DELETE")
                    creative_before = read_text(client_log).count("DEBUG_CREATIVE_DELETE")

                    # Phase 3: switch back happened at tick 200; hover a creative-list slot.
                    deadline = time.time() + 60
                    list_line = None
                    while time.time() < deadline:
                        text = read_text(client_log)
                        if "RES_TAB_BACK default" in text:
                            for line in text.splitlines():
                                if ("RES_SLOT" in line and "container=class_1277" in line
                                        and "item=minecraft:" in line):
                                    list_line = line
                            if list_line:
                                break
                        if client.poll() is not None:
                            break
                        time.sleep(1)
                    list_ignored = False
                    if list_line:
                        deadline_key2 = time.time() + 120
                        while time.time() < deadline_key2:
                            if any("RES_KEY phase=list" in line
                                   for line in read_text(client_log).splitlines()):
                                break
                            if client.poll() is not None:
                                break
                            time.sleep(1)
                        time.sleep(4)
                        deletes_after2 = read_text(server_log).count("SERVER_DELETE")
                        creative_after = read_text(client_log).count("DEBUG_CREATIVE_DELETE")
                        list_ignored = (deletes_after2 == deletes_before2
                                        and creative_after == creative_before)
                    else:
                        print("no creative-list dump line after tab switch", file=sys.stderr)
                    _grab_window(str(RUN / "after-list-delete.png"), client.pid)

                    text = read_text(client_log)
                    ser = read_text(server_log)
                    server_deletes = [line.split("SERVER_DELETE ", 1)[1]
                                      for line in ser.splitlines() if "SERVER_DELETE " in line]
                    states = [line.split("SERVER_STATE ", 1)[1]
                              for line in ser.splitlines() if "SERVER_STATE " in line]
                    main_deleted = (any(d.startswith("slot=18 ") for d in server_deletes)
                                    and states and "inv18=empty" in states[-1])
                    inv_dump_line = next((line for line in text.splitlines()
                                          if ("RES_SLOT" in line
                                              and "container=class_1661" in line
                                              and "item=minecraft:diamondx7" in line)), "")
                    result = {
                        "inventory_tab_line": inv_dump_line.split("RES_SLOT ", 1)[1]
                            if inv_dump_line else "",
                        "canvas_line": next(
                            (line.split("RES_CANVAS ", 1)[1]
                             for line in text.splitlines() if "RES_CANVAS" in line), ""),
                        "server_deletes": server_deletes,
                        "server_states_tail": states[-6:],
                        "main_inv_deleted": main_deleted,
                        "list_ignored": list_ignored,
                        "client_tail": text.splitlines()[-16:],
                        "server_tail": ser.splitlines()[-12:],
                    }
                    (RUN / "result.json").write_text(
                        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    print(json.dumps({k: result[k] for k in
                                      ("main_inv_deleted", "list_ignored",
                                       "server_deletes", "server_states_tail")},
                                     ensure_ascii=False))
                    return 0 if (main_deleted and list_ignored) else 1
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


if __name__ == "__main__":
    sys.exit(main())
