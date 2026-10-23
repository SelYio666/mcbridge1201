#!/usr/bin/env python3
"""p183: exercise the real TrashSlot empty-trash key path on a dedicated server.

Starts the Fabric server, installs the patched TrashSlot client jar on both sides, launches the
client with the trashkey probe, waits for the open inventory + geometry, moves the real cursor over
the trash slot and injects Delete, then checks the key/run/provider/server logs and screenshots the
inventory.
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
TRASH_JAR = ROOT / "work" / "client" / "trashslot-client-empty.jar"
BALM = SERVER_MODS / "balm-fabric-1.21.1.jar"
FABRIC_API = SERVER_MODS / "fabric-api-0.102.0+1.21.1.jar"
if not FABRIC_API.exists():
    FABRIC_API = SERVER_MODS / "fabric-api.jar"
PROBE = ROOT / "work" / "tmp" / "trashkey.jar"
PORT = "25566"
USER = "TrashKey"

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
    backup = ROOT / "work" / "tmp" / "p183-mod-backup"
    backup.mkdir(parents=True, exist_ok=True)
    for path in SERVER_MODS.glob("*.jar"):
        shutil.copy2(path, backup / path.name)
    for path in CLIENT_MODS.glob("*.jar"):
        shutil.copy2(path, backup / f"client-{path.name}")
    for path in CLIENT_MODS.glob("*.jar"):
        path.unlink()
    # Client: Fabric API, Balm, patched TrashSlot, probe.
    shutil.copy2(FABRIC_API, CLIENT_MODS / FABRIC_API.name)
    shutil.copy2(BALM, CLIENT_MODS / BALM.name)
    shutil.copy2(TRASH_JAR, CLIENT_MODS / "trashslot-client-empty.jar")
    shutil.copy2(PROBE, CLIENT_MODS / "trashkey.jar")
    # Server: same patched TrashSlot + probe, keep the server-only codecprobe.
    for name in ("trashslot-15.1.5+1.21.1.jar", "trashslot-client-empty.jar"):
        (SERVER_MODS / name).unlink(missing_ok=True)
    shutil.copy2(TRASH_JAR, SERVER_MODS / "trashslot-15.1.5+1.21.1.jar")
    for src in (FABRIC_API, BALM):
        dst = SERVER_MODS / src.name
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
    shutil.copy2(PROBE, SERVER_MODS / "trashkey.jar")


def set_server_port() -> None:
    props = SERVER / "server.properties"
    backup = RUN / "server.properties.before"
    if props.exists():
        shutil.copy2(props, backup)
        text = props.read_text(encoding="utf-8", errors="replace")
        lines = []
        for line in text.splitlines():
            if line.startswith("server-port="):
                line = f"server-port={PORT}"
            lines.append(line)
        if not any(line.startswith("server-port=") for line in lines):
            lines.append(f"server-port={PORT}")
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
    time.sleep(1)


def press_delete(hwnd: int) -> None:
    user32 = ctypes.windll.user32
    # VK_DELETE is an extended key (scan 0x53). Without KEYEVENTF_EXTENDEDKEY the game receives
    # GLFW_KEY_KP_DECIMAL (330), which is why the earlier p65 Delete attempts did nothing.
    extended = 0x0001
    keyup = 0x0002
    user32.keybd_event(0x2E, 0x53, extended, 0)
    time.sleep(0.15)
    user32.keybd_event(0x2E, 0x53, extended | keyup, 0)
    time.sleep(0.5)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    (ROOT / "work" / "tmp").mkdir(parents=True, exist_ok=True)
    if not PROBE.exists():
        print(f"missing probe jar: {PROBE}; run build.py first", file=sys.stderr)
        return 2
    setup_mods()
    set_server_port()

    java_home = os.environ.get("JAVA_HOME") or str(ROOT.parent / ".toolchain" / "jdk")
    java = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java")
    server_log = RUN / "server.log"
    server_log.write_text("", encoding="utf-8")
    print("starting dedicated server...")
    with server_log.open("w", encoding="utf-8", errors="replace") as out:
        server = subprocess.Popen([str(java), "-Xmx2G", "-jar", "fabric-server-launch.jar", "nogui"],
                                  cwd=str(SERVER), stdout=out, stderr=subprocess.STDOUT)
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
            server.terminate()
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
                geometry = None
                while time.time() < deadline:
                    text = read_text(client_log)
                    for line in text.splitlines():
                        if "KEY_SCREEN " in line:
                            fields = {}
                            for part in line.split("KEY_SCREEN ", 1)[1].split():
                                if "=" in part:
                                    k, v = part.split("=", 1)
                                    fields[k] = v
                            geometry = fields
                            break
                    if geometry:
                        break
                    if client.poll() is not None:
                        break
                    time.sleep(1)
                if not geometry:
                    print("no KEY_SCREEN marker; client tail:")
                    print("\n".join(read_text(client_log).splitlines()[-12:]))
                    return 1
                print("geometry:", geometry)
                hwnd = find_window(client.pid)
                if not hwnd:
                    print("no client window for pid", client.pid, file=sys.stderr)
                    return 1
                scale = float(geometry.get("scale", "3"))
                gui_x = float(geometry["left"]) + float(geometry["trashX"]) + 8
                gui_y = float(geometry["top"]) + float(geometry["trashY"]) + 8
                user32 = ctypes.windll.user32
                rect = ctypes.wintypes.RECT()
                user32.GetClientRect(hwnd, ctypes.byref(rect))
                origin = ctypes.wintypes.POINT(0, 0)
                user32.ClientToScreen(hwnd, ctypes.byref(origin))
                px = origin.x + int(gui_x * scale)
                py = origin.y + int(gui_y * scale)
                print(f"clicking trash at gui=({gui_x:.1f},{gui_y:.1f}) physical=({px},{py})")
                focus_and_click(hwnd, px, py)
                time.sleep(1)
                print("pressing Delete")
                press_delete(hwnd)
                time.sleep(3)
                _grab_window(str(RUN / "after.png"), client.pid)
                text = read_text(client_log)
                ser = read_text(server_log)
                key_seen = "DEBUG_KEY key=261" in text
                run_seen = "DEBUG_RUN " in text
                provider_seen = "DEBUG_EMPTY_PROVIDER" in text
                server_empty = any("SERVER_TRASH empty=true" in line for line in ser.splitlines())
                result = {
                    "geometry": geometry,
                    "physical": [px, py],
                    "key_seen": key_seen,
                    "run_seen": run_seen,
                    "provider_seen": provider_seen,
                    "server_empty": server_empty,
                    "client_tail": text.splitlines()[-20:],
                    "server_tail": ser.splitlines()[-20:],
                }
                (RUN / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")
                print(json.dumps({k: result[k] for k in ("key_seen", "run_seen", "provider_seen",
                                                         "server_empty")}, ensure_ascii=False))
                return 0 if (key_seen and run_seen and provider_seen and server_empty) else 1
            finally:
                if client.poll() is None:
                    client.terminate()
                    try:
                        client.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        client.kill()
                if server.poll() is None:
                    server.terminate()
                    try:
                        server.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        server.kill()
        # server finally
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
        for name, dest in (("logs/latest.log", "latest-server.log"),):
            src = SERVER / name
            if src.exists():
                shutil.copy2(src, RUN / dest)
        return 1


if __name__ == "__main__":
    sys.exit(main())
