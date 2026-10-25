#!/usr/bin/env python3
"""p189: TrashSlot creative-mode delete keys (Delete + Shift+Delete) in the real GUI.

Dedicated server with gamemode=creative; the item placement uses the server console
(`/item replace entity GridUser container.N with minecraft:diamond 5`) so the client's creative
inventory hotbar really holds diamonds. The client opens the creative screen; TrashSlot's creative
branch (enableDeleteKeysInCreative=true) must route Delete/Shift+Delete on the hovered hotbar slot
through CreativeDeletionProvider to the server. Creative semantics: every delete also empties the
trash (CreativeDeletionProvider.emptyTrashSlot).

Without the trashcreative-fix companion this scenario cannot pass at all: the 1.21.1 creative
screen (class_481) keeps AbstractContainerScreen.hoveredSlot null and has no SlotWrapper, so the
converted creative branch can never fire (see README).
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
PROBE = ROOT / "work" / "tmp" / "trashcreative.jar"
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
    backup = ROOT / "work" / "tmp" / "p189-mod-backup"
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
    shutil.copy2(PROBE, CLIENT_MODS / "trashcreative.jar")
    shutil.copy2(COMPANION, CLIENT_MODS / "trashcreative-fix.jar")
    for name in ("trashslot-15.1.5+1.21.1.jar", "trashslot-client-empty.jar"):
        (SERVER_MODS / name).unlink(missing_ok=True)
    shutil.copy2(TRASH_JAR, SERVER_MODS / "trashslot-15.1.5+1.21.1.jar")
    for src in (FABRIC_API, BALM):
        dst = SERVER_MODS / src.name
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
    shutil.copy2(PROBE, SERVER_MODS / "trashcreative.jar")


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
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, flags)  # HWND_TOPMOST
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


def press_delete() -> None:
    user32 = ctypes.windll.user32
    extended = 0x0001
    keyup = 0x0002
    user32.keybd_event(0x2E, 0x53, extended, 0)
    time.sleep(0.15)
    user32.keybd_event(0x2E, 0x53, extended | keyup, 0)
    time.sleep(0.5)


def press_shift_delete() -> None:
    user32 = ctypes.windll.user32
    extended = 0x0001
    keyup = 0x0002
    user32.keybd_event(0x10, 0x2A, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(0x2E, 0x53, extended, 0)
    time.sleep(0.15)
    user32.keybd_event(0x2E, 0x53, extended | keyup, 0)
    time.sleep(0.1)
    user32.keybd_event(0x10, 0x2A, keyup, 0)
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
    set_server_config()

    # Wipe the player so force-gamemode=creative really applies.
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
    items_sent = False
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
                    geom = []
                    while time.time() < deadline:
                        text = read_text(client_log)
                        if not items_sent and "CRE_OPEN" in text:
                            items_sent = True
                            for slot, count in ((0, 5), (1, 3)):
                                server.stdin.write((
                                    f"item replace entity {USER} container.{slot}"
                                    f" with minecraft:diamond {count}\n").encode("utf-8"))
                            server.stdin.flush()
                            print("sent /item replace for hotbar 0 (5) and 1 (3)")
                        if "CRE_SLOT" in text and items_sent:
                            geom = [line for line in text.splitlines()
                                    if "CRE_SLOT" in line
                                    and "item=minecraft:diamondx5" in line
                                    and "container=class_1661" in line]
                            if geom:
                                break
                        if client.poll() is not None:
                            break
                        time.sleep(1)
                    if not geom:
                        print("no CRE_SLOT with the diamond hotbar slot; client tail:")
                        print("\n".join(read_text(client_log).splitlines()[-14:]))
                        return 1
                    fields = {}
                    for part in geom[-1].split("CRE_SLOT ", 1)[1].split():
                        if "=" in part:
                            k, v = part.split("=", 1)
                            fields[k] = v
                    print("geometry:", fields)
                    hwnd = find_window(client.pid)
                    if not hwnd:
                        print("no client window for pid", client.pid, file=sys.stderr)
                        return 1
                    scale = float(fields.get("scale", "2"))
                    user32 = ctypes.windll.user32
                    origin = ctypes.wintypes.POINT(0, 0)
                    user32.ClientToScreen(hwnd, ctypes.byref(origin))
                    sx = float(fields["left"]) + float(fields["x"]) + 8
                    sy = float(fields["top"]) + float(fields["y"]) + 8
                    px = origin.x + int(sx * scale)
                    py = origin.y + int(sy * scale)
                    print(f"hovering hotbar diamond slot at physical=({px},{py})")

                    def focus_until() -> bool:
                        for _ in range(4):
                            focus_and_click(hwnd, px, py)
                            if user32.GetForegroundWindow() == hwnd:
                                return True
                            time.sleep(0.8)
                        return False

                    if not focus_until():
                        print("could not focus the game window", file=sys.stderr)
                    time.sleep(1)

                    def count_debug() -> int:
                        return read_text(client_log).count("DEBUG_KEY")

                    def press_until_logged(press, expect: str) -> bool:
                        for _ in range(4):
                            before = count_debug()
                            press()
                            time.sleep(2.5)
                            text_now = read_text(client_log)
                            if text_now.count("DEBUG_KEY") > before and expect in text_now:
                                return True
                            focus_until()
                        return False

                    # 1) Shift+Delete on hotbar 0 while hotbar 1 holds the same item: the delete_all
                    #    chain must clear BOTH slots (upstream semantics, p184 on the survival GUI).
                    print("pressing Shift+Delete (creative delete_all chain)")
                    if not press_until_logged(press_shift_delete,
                                              "DEBUG_CREATIVE_DELETE slot=36 all=true"):
                        print("Shift+Delete never reached the handler", file=sys.stderr)
                    time.sleep(2.5)
                    _grab_window(str(RUN / "after-delete-all.png"), client.pid)
                    # 2) refill hotbar 0 and verify the plain creative Delete on the same slot.
                    server.stdin.write((f"item replace entity {USER} container.0"
                                        " with minecraft:diamond 5\n").encode("utf-8"))
                    server.stdin.flush()
                    time.sleep(1.5)
                    print("pressing Delete (creative delete)")
                    if not press_until_logged(press_delete,
                                              "DEBUG_CREATIVE_DELETE slot=36 all=false"):
                        print("Delete never reached the handler", file=sys.stderr)
                    time.sleep(2.5)
                    _grab_window(str(RUN / "after.png"), client.pid)
                    text = read_text(client_log)
                    ser = read_text(server_log)
                    server_states = [line.split("SERVER_STATE ", 1)[1]
                                     for line in ser.splitlines() if "SERVER_STATE " in line]
                    server_deletes = [line.split("SERVER_DELETE ", 1)[1]
                                      for line in ser.splitlines() if "SERVER_DELETE " in line]
                    result = {
                        "geometry": fields,
                        "physical": [px, py],
                        "creative_delete_seen": text.count("DEBUG_CREATIVE_DELETE slot="),
                        "delete_all_seen": "all=true" in text,
                        "server_deletes": server_deletes,
                        "server_states_tail": server_states[-6:],
                        "client_tail": text.splitlines()[-20:],
                        "server_tail": ser.splitlines()[-12:],
                    }
                    (RUN / "result.json").write_text(
                        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    # Gate: both creative deletes ran; the server menu was the InventoryMenu; the
                    # delete_all chain emptied BOTH hotbar slots; trash stayed empty (creative).
                    ok = (result["creative_delete_seen"] >= 2 and result["delete_all_seen"]
                          and any(d.startswith("slot=36 all=true") for d in server_deletes)
                          and server_states[-1].count("empty") >= 3)
                    print(json.dumps({k: result[k] for k in
                                      ("creative_delete_seen", "delete_all_seen",
                                       "server_deletes", "server_states_tail")},
                                     ensure_ascii=False))
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


if __name__ == "__main__":
    sys.exit(main())
